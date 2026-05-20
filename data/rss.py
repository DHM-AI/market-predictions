"""
RSS feed agent — pulls SEC filings, earnings alerts, and analyst upgrades.
All sources are free, no API key required.
"""
import feedparser
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta

FEEDS = {
    "sec_8k": "https://www.sec.gov/cgi-bin/browse-edgar?action=getcurrent&type=8-K&dateb=&owner=include&count=40&output=atom",
    "sec_insider": "https://www.sec.gov/cgi-bin/browse-edgar?action=getcurrent&type=4&dateb=&owner=include&count=40&output=atom",
    "seekingalpha": "https://seekingalpha.com/market_currents.xml",
    "marketwatch": "https://feeds.content.dowjones.io/public/rss/mw_marketpulse",
    "yahoo_finance": "https://finance.yahoo.com/news/rssindex",
}

BULLISH_WORDS = {"beat", "upgrade", "outperform", "buy", "exceed", "record",
                 "growth", "profit", "strong", "raise", "positive", "surge"}
BEARISH_WORDS = {"miss", "downgrade", "underperform", "sell", "loss", "weak",
                 "decline", "cut", "negative", "warning", "recall", "fraud"}

HEADERS = {"User-Agent": "market-predictions/1.0 renato@deltahubmedia.com"}


def _fetch_feed(url: str) -> list[dict]:
    try:
        resp = requests.get(url, headers=HEADERS, timeout=10)
        feed = feedparser.parse(resp.text)
        entries = []
        cutoff = datetime.now() - timedelta(days=2)
        for e in feed.entries:
            title = e.get("title", "")
            summary = e.get("summary", "")
            entries.append({"title": title, "summary": summary})
        return entries
    except Exception:
        return []


def _score_entry(entry: dict, ticker: str) -> float | None:
    text = (entry.get("title", "") + " " + entry.get("summary", "")).lower()
    if ticker.lower() not in text and f"${ticker.lower()}" not in text:
        return None  # not relevant to this ticker
    words = set(text.split())
    bull = len(words & BULLISH_WORDS)
    bear = len(words & BEARISH_WORDS)
    total = bull + bear
    if total == 0:
        return 0.0
    return (bull - bear) / total


def get_rss_sentiment(ticker: str) -> dict:
    """
    Pull all RSS feeds and score entries mentioning the ticker.
    """
    all_entries = []
    with ThreadPoolExecutor(max_workers=len(FEEDS)) as ex:
        futures = {ex.submit(_fetch_feed, url): name
                   for name, url in FEEDS.items()}
        for f in as_completed(futures):
            all_entries.extend(f.result())

    scores = []
    for entry in all_entries:
        s = _score_entry(entry, ticker)
        if s is not None:
            scores.append(s)

    if not scores:
        return {"score": 0.0, "article_count": 0, "source": "rss"}

    return {
        "score": round(sum(scores) / len(scores), 4),
        "article_count": len(scores),
        "source": "rss",
    }


def get_rss_sentiment_batch(tickers: list[str],
                            max_workers: int = 20) -> dict[str, dict]:
    """Fetch all RSS feeds once, then score each ticker against them."""
    # Fetch all feeds once (shared)
    all_entries = []
    with ThreadPoolExecutor(max_workers=len(FEEDS)) as ex:
        futures = [ex.submit(_fetch_feed, url) for url in FEEDS.values()]
        for f in as_completed(futures):
            all_entries.extend(f.result())

    results = {}
    for ticker in tickers:
        scores = []
        for entry in all_entries:
            s = _score_entry(entry, ticker)
            if s is not None:
                scores.append(s)
        results[ticker] = {
            "score": round(sum(scores) / len(scores), 4) if scores else 0.0,
            "article_count": len(scores),
            "source": "rss",
        }
    return results
