from __future__ import annotations
"""
Parallel research coordinator — runs all sentiment sources simultaneously.

Sources (all free, no paid API required):
  1. Alpha Vantage news sentiment (25 req/day)
  2. yfinance news headlines
  3. Reddit (public JSON API — no auth)
  4. RSS feeds (SEC, Yahoo Finance, MarketWatch)

Aggregates into a single blended sentiment score per ticker.
"""
from concurrent.futures import ThreadPoolExecutor, as_completed
from data.news import get_sentiment as get_av_yf_sentiment
from data.reddit import get_reddit_sentiment_batch
from data.rss import get_rss_sentiment_batch
from data.stocktwits import get_stocktwits_sentiment_batch


# Rebalanced 2026-05-28 — added StockTwits as 5th source.
# StockTwits gets meaningful weight (0.20) because its Bull/Bear voting is
# higher-signal than scraped Reddit text. Reddit dropped 0.30→0.25.
SOURCE_WEIGHTS = {
    "alpha_vantage": 0.30,
    "yfinance":      0.10,
    "reddit":        0.25,
    "rss":           0.15,
    "stocktwits":    0.20,
}


def _blend_scores(av_yf: dict, reddit: dict, rss: dict, stocktwits: dict) -> dict:
    av_score = av_yf.get("score", 0.0)
    rd_score = reddit.get("score", 0.0)
    rs_score = rss.get("score", 0.0)
    st_score = stocktwits.get("score", 0.0)

    source = av_yf.get("source", "yfinance")
    av_w = SOURCE_WEIGHTS["alpha_vantage"] if source == "alpha_vantage" else 0.0
    yf_w = SOURCE_WEIGHTS["yfinance"]      if source != "alpha_vantage" else 0.0
    rd_w = SOURCE_WEIGHTS["reddit"]
    rs_w = SOURCE_WEIGHTS["rss"]
    st_w = SOURCE_WEIGHTS["stocktwits"]

    total_w = av_w + yf_w + rd_w + rs_w + st_w
    blended = (av_score * (av_w + yf_w)
               + rd_score * rd_w
               + rs_score * rs_w
               + st_score * st_w) / total_w

    return {
        "score":               round(blended, 4),
        "av_score":            av_score,
        "reddit_score":        rd_score,
        "rss_score":           rs_score,
        "stocktwits_score":    st_score,
        "reddit_mentions":     reddit.get("mention_count", 0),
        "reddit_upvotes":      reddit.get("upvote_total", 0),
        "rss_articles":        rss.get("article_count", 0),
        "stocktwits_messages": stocktwits.get("message_count", 0),
        "stocktwits_bull":     stocktwits.get("bullish_count", 0),
        "stocktwits_bear":     stocktwits.get("bearish_count", 0),
        "source":              f"blended({source}+reddit+rss+stocktwits)",
    }


def research_universe(tickers: list[str],
                      max_workers: int = 20) -> dict[str, dict]:
    """
    Run all research sources in parallel for the full ticker universe.
    Returns {ticker: blended_sentiment_dict}
    """
    print(f"[research] Starting parallel research for {len(tickers)} tickers...")

    # Reddit batch (one pass, all tickers in parallel)
    print("[research] Fetching Reddit sentiment...")
    reddit_map = get_reddit_sentiment_batch(tickers, max_workers=max_workers)

    # RSS batch (fetch feeds once, score all tickers)
    print("[research] Fetching RSS feeds...")
    rss_map = get_rss_sentiment_batch(tickers, max_workers=max_workers)

    # StockTwits batch — cashtag-based trader sentiment with Bull/Bear voting
    print("[research] Fetching StockTwits sentiment...")
    stocktwits_map = get_stocktwits_sentiment_batch(tickers, max_workers=max_workers)

    # AV/yfinance per ticker (rate-limited, run with limited workers)
    print("[research] Fetching news sentiment (AV/yfinance)...")
    av_map: dict[str, dict] = {}
    with ThreadPoolExecutor(max_workers=5) as ex:
        futures = {ex.submit(get_av_yf_sentiment, t): t for t in tickers}
        for i, f in enumerate(as_completed(futures)):
            t = futures[f]
            try:
                av_map[t] = f.result()
            except Exception:
                av_map[t] = {"score": 0.0, "source": "yfinance"}
            if (i + 1) % 100 == 0:
                print(f"  {i+1}/{len(tickers)} news scores done")

    # Blend all sources
    blended = {}
    for ticker in tickers:
        blended[ticker] = _blend_scores(
            av_map.get(ticker, {"score": 0.0, "source": "yfinance"}),
            reddit_map.get(ticker, {"score": 0.0, "mention_count": 0}),
            rss_map.get(ticker, {"score": 0.0, "article_count": 0}),
            stocktwits_map.get(ticker, {"score": 0.0, "message_count": 0,
                                        "bullish_count": 0, "bearish_count": 0}),
        )

    high_signal = sum(1 for v in blended.values() if abs(v["score"]) > 0.2)
    print(f"[research] Done. {high_signal} tickers with strong sentiment signal.")
    return blended
