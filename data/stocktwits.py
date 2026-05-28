"""
StockTwits sentiment agent — public stream API, no auth required.

Why StockTwits over X/Twitter:
  - Free (X API basic is $200/mo for limited reads)
  - Trader-focused — minimal political/meme noise
  - Cashtag native ($NVDA) so no false matches on common words
  - Built-in Bull/Bear sentiment voting per message
  - Active community for liquid US stocks

Endpoint:
  GET https://api.stocktwits.com/api/2/streams/symbol/{TICKER}.json
  Returns up to 30 most recent messages with .entities.sentiment.basic
  set to "Bullish" / "Bearish" / None.

Output shape mirrors data.reddit so research.py can blend it identically.
"""
import time
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed

_URL = "https://api.stocktwits.com/api/2/streams/symbol/{ticker}.json"
_HEADERS = {"User-Agent": "market-predictions/1.0 (research bot)"}
_TIMEOUT = 8

# Fallback keyword sentiment for messages with no explicit Bull/Bear tag
_BULLISH = {"buy", "long", "calls", "moon", "bull", "breakout", "squeeze",
            "upgrade", "beat", "strong", "surge", "rally", "undervalued",
            "ath", "rip", "lfg", "tendies"}
_BEARISH = {"sell", "short", "puts", "crash", "bear", "dump", "downgrade",
            "miss", "weak", "overvalued", "bubble", "drop", "fall", "rug",
            "rugpull", "tank", "selloff"}


def _keyword_score(text: str) -> float:
    """Fallback when StockTwits message has no Bull/Bear tag."""
    words = set((text or "").lower().split())
    b = len(words & _BULLISH)
    s = len(words & _BEARISH)
    total = b + s
    if total == 0:
        return 0.0
    return (b - s) / total   # [-1, 1]


def _fetch(ticker: str) -> list[dict]:
    """One HTTP call — returns the raw message list or []."""
    try:
        r = requests.get(_URL.format(ticker=ticker.upper()),
                         headers=_HEADERS, timeout=_TIMEOUT)
        if r.status_code != 200:
            return []
        return (r.json() or {}).get("messages", []) or []
    except Exception:
        return []


def get_stocktwits_sentiment(ticker: str) -> dict:
    """
    Returns {score, message_count, bullish_count, bearish_count, source}.

    score is in [-1, 1]:
      +1  fully bullish
       0  neutral / no data
      -1  fully bearish
    """
    msgs = _fetch(ticker)
    if not msgs:
        return {"score": 0.0, "message_count": 0,
                "bullish_count": 0, "bearish_count": 0,
                "source": "stocktwits"}

    bull = bear = 0
    scores = []
    for m in msgs:
        # Prefer explicit user tag — that's the highest-quality signal
        tag = ((m.get("entities") or {}).get("sentiment") or {}).get("basic")
        if tag == "Bullish":
            bull += 1
            scores.append(1.0)
        elif tag == "Bearish":
            bear += 1
            scores.append(-1.0)
        else:
            # No explicit tag — fall back to keyword score on body
            kw = _keyword_score(m.get("body", ""))
            if kw != 0:
                scores.append(kw)

    if not scores:
        return {"score": 0.0, "message_count": len(msgs),
                "bullish_count": bull, "bearish_count": bear,
                "source": "stocktwits"}

    avg = sum(scores) / len(scores)
    # Clamp + round (already in [-1, 1] by construction)
    return {
        "score":          round(max(-1.0, min(1.0, avg)), 4),
        "message_count":  len(msgs),
        "bullish_count":  bull,
        "bearish_count":  bear,
        "source":         "stocktwits",
    }


def get_stocktwits_sentiment_batch(tickers: list[str],
                                   max_workers: int = 10) -> dict[str, dict]:
    """Parallel fetch — gentle on the API (small sleep between completions)."""
    results: dict[str, dict] = {}
    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        futures = {ex.submit(get_stocktwits_sentiment, t): t for t in tickers}
        for f in as_completed(futures):
            ticker = futures[f]
            try:
                results[ticker] = f.result()
            except Exception:
                results[ticker] = {"score": 0.0, "message_count": 0,
                                   "bullish_count": 0, "bearish_count": 0,
                                   "source": "stocktwits"}
            time.sleep(0.05)
    return results
