from datetime import datetime, timedelta
from data.news import get_sentiment


def _load_cache() -> dict:
    try:
        import db
        if db.db_available():
            return db.load_sentiment_cache()
    except Exception:
        pass
    return {}


def get_sentiment_with_velocity(ticker: str) -> dict:
    """
    Returns current sentiment score and velocity (change vs 7 days ago).
    Persists scores to Supabase sentiment_cache table (falls back to in-memory if unavailable).
    """
    today = datetime.today().strftime("%Y-%m-%d")
    seven_days_ago = (datetime.today() - timedelta(days=7)).strftime("%Y-%m-%d")

    current = get_sentiment(ticker)
    score = current.get("score", 0.0)
    article_count = current.get("article_count", 0)

    # Persist to Supabase
    try:
        import db
        if db.db_available():
            db.save_sentiment_entry(ticker, today, score)
            db.prune_sentiment_cache(days=30)
    except Exception:
        pass

    # Compute velocity from cache
    cache = _load_cache()
    ticker_history = cache.get(ticker, {})
    prior_score = None
    for d in sorted(ticker_history.keys(), reverse=True):
        if d <= seven_days_ago:
            prior_score = ticker_history[d]
            break

    velocity = (score - prior_score) if prior_score is not None else 0.0
    spike = abs(velocity) >= 0.3

    return {
        "score": round(score, 4),
        "velocity": round(velocity, 4),
        "spike": spike,
        "article_count": article_count,
        "source": current.get("source", "unknown"),
    }


def normalize_score(score: float) -> float:
    """Map sentiment score [-1, 1] to [0, 1] for blending."""
    return (score + 1.0) / 2.0
