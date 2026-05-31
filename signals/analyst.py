from __future__ import annotations
"""
Analyst revisions signal — upgrade/downgrade momentum via yfinance.

When multiple analysts upgrade in a tight window, institutional money tends
to follow. Same for downgrades, in reverse. Captures fundamental sentiment
shift before it shows up in price.

Public API:
    get_analyst_signal(ticker, days=30) -> dict
        Returns:
          {
            "triggered": bool,
            "upgrades":   int,
            "downgrades": int,
            "net":        int,     # upgrades - downgrades
            "side":       "bull" | "bear" | "neutral",
            "strength":   float,   # 0..1
            "summary":    str,
          }

Cache: 24h in `analyst_cache` Supabase table:

    CREATE TABLE IF NOT EXISTS analyst_cache (
      ticker     TEXT PRIMARY KEY,
      checked_at TIMESTAMPTZ NOT NULL,
      payload    JSONB NOT NULL
    );
"""
import json
from datetime import datetime, timedelta, timezone

import pandas as pd
import yfinance as yf


_LOOKBACK_DAYS = 30
_MIN_NET       = 2     # net +2 upgrades = bullish, -2 = bearish
_CACHE_HOURS   = 24

# Map common yfinance "Action" values to a normalized buckets.
# yfinance returns things like "up", "down", "main", "init", "reit" — we want
# to know if rating direction is improving or worsening.
_UP_ACTIONS   = {"up", "init"}             # "main" = maintained/reiterated rating — NOT a directional upgrade
_DOWN_ACTIONS = {"down"}
# Grade strings — used as a secondary check when Action is missing.
_BULL_GRADES = {"buy", "strong buy", "outperform", "overweight", "positive", "accumulate", "long-term buy"}
_BEAR_GRADES = {"sell", "underperform", "underweight", "negative", "reduce"}


def _safe_supabase_client():
    try:
        from db import _client
        return _client()
    except Exception:
        return None


def _load_cached(ticker: str) -> dict | None:
    client = _safe_supabase_client()
    if client is None:
        return None
    try:
        res = (client.table("analyst_cache")
                     .select("checked_at,payload")
                     .eq("ticker", ticker)
                     .limit(1).execute())
        if not res.data:
            return None
        row = res.data[0]
        checked = datetime.fromisoformat(row["checked_at"].replace("Z", "+00:00"))
        if datetime.now(timezone.utc) - checked > timedelta(hours=_CACHE_HOURS):
            return None
        payload = row["payload"]
        if isinstance(payload, str):
            payload = json.loads(payload)
        return payload
    except Exception:
        return None


def _save_cached(ticker: str, payload: dict) -> None:
    client = _safe_supabase_client()
    if client is None:
        return
    try:
        client.table("analyst_cache").upsert({
            "ticker":     ticker,
            "checked_at": datetime.now(timezone.utc).isoformat(),
            "payload":    payload,
        }, on_conflict="ticker").execute()
    except Exception:
        pass


def _empty(reason: str = "") -> dict:
    return {
        "triggered":  False,
        "upgrades":   0,
        "downgrades": 0,
        "net":        0,
        "side":       "neutral",
        "strength":   0.0,
        "summary":    reason,
    }


def _classify_row(action: str, to_grade: str, from_grade: str) -> str:
    """Return 'up', 'down', or 'neutral' for a single revision row."""
    a = (action or "").strip().lower()
    if a in _UP_ACTIONS:
        return "up"
    if a in _DOWN_ACTIONS:
        return "down"

    # Fallback: compare to-grade against from-grade verbally
    tg = (to_grade or "").strip().lower()
    fg = (from_grade or "").strip().lower()
    if tg in _BULL_GRADES and fg in _BEAR_GRADES:
        return "up"
    if tg in _BEAR_GRADES and fg in _BULL_GRADES:
        return "down"
    if tg in _BULL_GRADES and fg not in _BULL_GRADES:
        return "up"
    if tg in _BEAR_GRADES and fg not in _BEAR_GRADES:
        return "down"
    return "neutral"


def get_analyst_signal(ticker: str, days: int = _LOOKBACK_DAYS) -> dict:
    """Score analyst upgrade/downgrade momentum over trailing window."""
    if not ticker:
        return _empty()

    cached = _load_cached(ticker)
    if cached is not None:
        return cached

    try:
        t = yf.Ticker(ticker)
        df = t.upgrades_downgrades
        if df is None or df.empty:
            sig = _empty("no analyst data")
            _save_cached(ticker, sig)
            return sig
    except Exception as e:
        return _empty(f"yfinance error: {e}")

    df = df.copy()
    # Normalize column names — yfinance uses 'Firm', 'ToGrade', 'FromGrade', 'Action', 'GradeDate'
    col_lower = {c.lower(): c for c in df.columns}

    # Date col can be index OR a GradeDate column.
    if "gradedate" in col_lower:
        df["__dt"] = pd.to_datetime(df[col_lower["gradedate"]], errors="coerce", utc=True)
    else:
        df["__dt"] = pd.to_datetime(df.index, errors="coerce", utc=True)

    cutoff = pd.Timestamp.now(tz="UTC") - pd.Timedelta(days=days)
    df = df[df["__dt"] >= cutoff]
    if df.empty:
        sig = _empty("no recent analyst revisions")
        _save_cached(ticker, sig)
        return sig

    action_col = col_lower.get("action", "")
    to_col     = col_lower.get("tograde", "")
    from_col   = col_lower.get("fromgrade", "")

    ups = 0
    downs = 0
    for _, row in df.iterrows():
        cls = _classify_row(
            str(row.get(action_col, "")) if action_col else "",
            str(row.get(to_col, ""))     if to_col     else "",
            str(row.get(from_col, ""))   if from_col   else "",
        )
        if cls == "up":
            ups += 1
        elif cls == "down":
            downs += 1

    net = ups - downs

    if net >= _MIN_NET:
        side = "bull"
        triggered = True
    elif net <= -_MIN_NET:
        side = "bear"
        triggered = True
    else:
        side = "neutral"
        triggered = False

    # Strength: scale by net revisions. 5+ net = max.
    strength = min(1.0, abs(net) / 5.0)

    if triggered and side == "bull":
        summary = f"Analyst upgrades (net +{net} in {days}d)"
    elif triggered and side == "bear":
        summary = f"Analyst downgrades (net {net} in {days}d)"
    else:
        summary = ""

    sig = {
        "triggered":  bool(triggered),
        "upgrades":   ups,
        "downgrades": downs,
        "net":        net,
        "side":       side,
        "strength":   round(strength, 3),
        "summary":    summary,
    }
    _save_cached(ticker, sig)
    return sig
