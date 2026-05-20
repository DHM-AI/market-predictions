"""
Supabase persistence layer — replaces logs/predictions.csv and logs/sentiment_cache.json.

Two tables:
  predictions     — one row per (date, ticker) prediction
  sentiment_cache — one row per (ticker, date) sentiment score
"""
import os
from datetime import datetime, timedelta

from supabase import create_client, Client

_SCHEMA_COLS = {
    "date", "ticker", "score", "direction", "duration", "confidence",
    "signals_triggered", "rsi", "bb_pct", "atr_ratio", "volume_ratio",
    "sentiment_score", "earnings_days", "xgb_prob", "actual_move_5d",
}


def get_client() -> Client:
    url = os.environ.get("SUPABASE_URL", "")
    key = os.environ.get("SUPABASE_KEY", "")
    if not url or not key:
        raise RuntimeError(
            "SUPABASE_URL and SUPABASE_KEY must be set in environment or .env"
        )
    return create_client(url, key)


# Streamlit-cached version (avoids reconnecting on every rerender)
try:
    import streamlit as st

    @st.cache_resource
    def get_cached_client() -> Client:
        return get_client()

except ImportError:
    get_cached_client = get_client  # type: ignore


def _client() -> Client:
    """Use cached client when running inside Streamlit, plain client elsewhere."""
    try:
        import streamlit as st
        return get_cached_client()
    except Exception:
        return get_client()


# ── Predictions ───────────────────────────────────────────────────────────────

def load_predictions() -> list[dict]:
    result = _client().table("predictions").select("*").order("date", desc=True).execute()
    return result.data or []


def load_predictions_for_date(date_str: str) -> list[dict]:
    result = (
        _client()
        .table("predictions")
        .select("*")
        .eq("date", date_str)
        .order("score", desc=True)
        .execute()
    )
    return result.data or []


def append_predictions(rows: list[dict]) -> None:
    if not rows:
        return
    # Strip columns not in the DB schema
    clean = [
        {k: (v if not isinstance(v, list) else "; ".join(str(i) for i in v))
         for k, v in r.items()
         if k in _SCHEMA_COLS}
        for r in rows
    ]
    _client().table("predictions").upsert(clean, on_conflict="date,ticker").execute()


def update_actual_move(date_str: str, ticker: str, move: float) -> None:
    (
        _client()
        .table("predictions")
        .update({"actual_move_5d": round(move, 2)})
        .eq("date", date_str)
        .eq("ticker", ticker)
        .execute()
    )


# ── Sentiment cache ───────────────────────────────────────────────────────────

def load_sentiment_cache() -> dict:
    """Return {ticker: {date_str: score}} for the last 30 days."""
    cutoff = (datetime.today() - timedelta(days=30)).strftime("%Y-%m-%d")
    result = (
        _client()
        .table("sentiment_cache")
        .select("ticker,date,score")
        .gte("date", cutoff)
        .execute()
    )
    cache: dict = {}
    for row in result.data or []:
        t = row["ticker"]
        d = str(row["date"])
        cache.setdefault(t, {})[d] = row["score"]
    return cache


def save_sentiment_entry(ticker: str, date_str: str, score: float) -> None:
    (
        _client()
        .table("sentiment_cache")
        .upsert(
            {"ticker": ticker, "date": date_str, "score": score},
            on_conflict="ticker,date",
        )
        .execute()
    )


def prune_sentiment_cache(days: int = 30) -> None:
    cutoff = (datetime.today() - timedelta(days=days)).strftime("%Y-%m-%d")
    _client().table("sentiment_cache").delete().lt("date", cutoff).execute()


def db_available() -> bool:
    """Return True if Supabase credentials are configured."""
    return bool(os.environ.get("SUPABASE_URL") and os.environ.get("SUPABASE_KEY"))


# ── Learnings ─────────────────────────────────────────────────────────────────

def save_learning(record: dict) -> None:
    _client().table("learnings").insert(record).execute()


def load_learnings() -> list[dict]:
    result = _client().table("learnings").select("*").order("week_of", desc=True).execute()
    return result.data or []


# ── Trades ────────────────────────────────────────────────────────────────────

def save_trade(record: dict) -> None:
    """Save an Alpaca trade execution record."""
    _client().table("trades").upsert(record, on_conflict="order_id").execute()


def load_trades() -> list[dict]:
    result = _client().table("trades").select("*").order("timestamp", desc=True).execute()
    return result.data or []
