import os
import requests
from data.fetcher import get_recent_news
from config import ALPHA_VANTAGE_KEY

BULLISH_WORDS = {"beat", "surge", "upgrade", "breakout", "record", "rally",
                 "growth", "profit", "exceed", "outperform", "buy", "strong"}
BEARISH_WORDS = {"miss", "downgrade", "crash", "recall", "fraud", "loss",
                 "decline", "weak", "cut", "layoff", "lawsuit", "warning"}


def _keyword_score(text: str) -> float:
    words = set(text.lower().split())
    bull = len(words & BULLISH_WORDS)
    bear = len(words & BEARISH_WORDS)
    total = bull + bear
    if total == 0:
        return 0.0
    return (bull - bear) / total


def get_av_sentiment(ticker: str) -> dict:
    if not ALPHA_VANTAGE_KEY:
        return {}
    url = (
        f"https://www.alphavantage.co/query"
        f"?function=NEWS_SENTIMENT&tickers={ticker}"
        f"&limit=20&apikey={ALPHA_VANTAGE_KEY}"
    )
    try:
        resp = requests.get(url, timeout=10)
        data = resp.json()
        feed = data.get("feed", [])
        if not feed:
            return {}
        scores = []
        for article in feed:
            for ts in article.get("ticker_sentiment", []):
                if ts.get("ticker") == ticker:
                    try:
                        scores.append(float(ts["ticker_sentiment_score"]))
                    except (KeyError, ValueError):
                        pass
        if not scores:
            return {}
        avg = sum(scores) / len(scores)
        return {"score": avg, "article_count": len(feed), "source": "alpha_vantage"}
    except Exception:
        return {}


def get_yf_sentiment(ticker: str) -> dict:
    news = get_recent_news(ticker)
    if not news:
        return {"score": 0.0, "article_count": 0, "source": "yfinance"}
    scores = []
    for item in news:
        title = item.get("title", "")
        if title:
            scores.append(_keyword_score(title))
    if not scores:
        return {"score": 0.0, "article_count": 0, "source": "yfinance"}
    return {
        "score": sum(scores) / len(scores),
        "article_count": len(scores),
        "source": "yfinance",
    }


def get_sentiment(ticker: str) -> dict:
    result = get_av_sentiment(ticker)
    if result:
        return result
    return get_yf_sentiment(ticker)


def get_sentiment_delta(current_score: float, prior_score: float) -> float:
    return current_score - prior_score
