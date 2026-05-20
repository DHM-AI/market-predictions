"""
Reddit sentiment agent — uses public JSON API, no credentials required.
Scrapes r/wallstreetbets, r/stocks, r/investing for ticker mentions.
"""
import requests
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

SUBREDDITS = ["wallstreetbets", "stocks", "investing", "options", "StockMarket"]
HEADERS = {"User-Agent": "market-predictions/1.0 (research bot)"}
BULLISH = {"buy", "long", "calls", "moon", "rocket", "bull", "breakout", "squeeze",
           "upgrade", "beat", "strong", "surge", "rally", "undervalued"}
BEARISH = {"sell", "short", "puts", "crash", "bear", "dump", "downgrade", "miss",
           "weak", "overvalued", "bubble", "drop", "fall", "recession"}


def _search_subreddit(subreddit: str, ticker: str, limit: int = 25) -> list[dict]:
    url = f"https://www.reddit.com/r/{subreddit}/search.json"
    params = {"q": ticker, "sort": "new", "restrict_sr": 1,
              "limit": limit, "t": "week"}
    try:
        resp = requests.get(url, headers=HEADERS, params=params, timeout=8)
        if resp.status_code != 200:
            return []
        data = resp.json()
        posts = data.get("data", {}).get("children", [])
        return [p["data"] for p in posts]
    except Exception:
        return []


def _score_post(post: dict) -> float:
    text = (post.get("title", "") + " " + post.get("selftext", "")).lower()
    words = set(text.split())
    bull = len(words & BULLISH)
    bear = len(words & BEARISH)
    upvotes = post.get("ups", 0)
    weight = 1 + min(upvotes / 1000, 3)  # upvoted posts count more, max 4x
    total = bull + bear
    if total == 0:
        return 0.0
    return ((bull - bear) / total) * weight


def get_reddit_sentiment(ticker: str) -> dict:
    """
    Returns aggregated sentiment across all subreddits for a ticker.
    Result: {score, mention_count, upvote_total, source}
    """
    all_posts = []
    with ThreadPoolExecutor(max_workers=len(SUBREDDITS)) as ex:
        futures = {ex.submit(_search_subreddit, sub, ticker): sub
                   for sub in SUBREDDITS}
        for f in as_completed(futures):
            all_posts.extend(f.result())

    if not all_posts:
        return {"score": 0.0, "mention_count": 0, "upvote_total": 0, "source": "reddit"}

    scores = [_score_post(p) for p in all_posts]
    upvote_total = sum(p.get("ups", 0) for p in all_posts)
    avg_score = sum(scores) / len(scores)

    # Normalize to [-1, 1]
    normalized = max(-1.0, min(1.0, avg_score / 4.0))

    return {
        "score": round(normalized, 4),
        "mention_count": len(all_posts),
        "upvote_total": upvote_total,
        "source": "reddit",
    }


def get_reddit_sentiment_batch(tickers: list[str],
                               max_workers: int = 10) -> dict[str, dict]:
    """Fetch Reddit sentiment for multiple tickers in parallel."""
    results = {}
    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        futures = {ex.submit(get_reddit_sentiment, t): t for t in tickers}
        for f in as_completed(futures):
            ticker = futures[f]
            try:
                results[ticker] = f.result()
            except Exception:
                results[ticker] = {"score": 0.0, "mention_count": 0,
                                   "upvote_total": 0, "source": "reddit"}
            time.sleep(0.1)  # gentle rate limiting
    return results
