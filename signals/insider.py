from __future__ import annotations
"""
Insider activity signal — SEC Form 4 filings via yfinance.

Form 4 must be filed within 2 business days of any insider transaction
(officer, director, or 10%+ owner). Cluster insider buying is a known
leading indicator — insiders see things the market doesn't.

Public API:
    get_insider_signal(ticker, days=90) -> dict
        Returns:
          {
            "triggered":     bool,    # cluster buy detected
            "buy_count":     int,     # # of distinct insider buys in window
            "sell_count":    int,
            "buy_dollar":    float,
            "sell_dollar":   float,
            "net_dollar":    float,   # buy - sell
            "side":          "bull" | "bear" | "neutral",
            "strength":      float,   # 0..1
            "summary":       str,     # human-readable for signals_triggered list
          }

Cache: results stored 24h in `insider_cache` Supabase table to avoid
hammering Yahoo on every scan. Add the table once:

    CREATE TABLE IF NOT EXISTS insider_cache (
      ticker     TEXT PRIMARY KEY,
      checked_at TIMESTAMPTZ NOT NULL,
      payload    JSONB NOT NULL
    );
"""
import json
from datetime import datetime, timedelta, timezone

import pandas as pd
import yfinance as yf


# Tuning knobs
_LOOKBACK_DAYS         = 90
_MIN_BUYS_FOR_CLUSTER  = 3      # ≥3 distinct insider buys in window = cluster
_MIN_NET_DOLLAR        = 250_000  # filter out trivial transactions
_CACHE_HOURS           = 24


def _safe_supabase_client():
    """Return a Supabase client if available, else None (signal still works)."""
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
        res = (client.table("insider_cache")
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
        client.table("insider_cache").upsert({
            "ticker":     ticker,
            "checked_at": datetime.now(timezone.utc).isoformat(),
            "payload":    payload,
        }, on_conflict="ticker").execute()
    except Exception:
        pass


def _empty_signal(reason: str = "") -> dict:
    return {
        "triggered":   False,
        "buy_count":   0,
        "sell_count":  0,
        "buy_dollar":  0.0,
        "sell_dollar": 0.0,
        "net_dollar":  0.0,
        "side":        "neutral",
        "strength":    0.0,
        "summary":     reason,
    }


def get_insider_signal(ticker: str, days: int = _LOOKBACK_DAYS) -> dict:
    """Fetch + score insider transactions. Cached 24h in Supabase."""
    if not ticker:
        return _empty_signal()

    cached = _load_cached(ticker)
    if cached is not None:
        return cached

    try:
        t = yf.Ticker(ticker)
        # yfinance returns a DataFrame with columns roughly:
        # Insider | Position | URL | Transaction | Text | SEC Form 4 | (date)
        # Some fields vary by version — we defensively handle either schema.
        df = t.insider_transactions
        if df is None or df.empty:
            sig = _empty_signal("no insider data")
            _save_cached(ticker, sig)
            return sig
    except Exception as e:
        return _empty_signal(f"yfinance error: {e}")

    # Normalize column names — yfinance sometimes returns different casings
    df = df.copy()
    df.columns = [c.strip() for c in df.columns]
    col_map = {c.lower(): c for c in df.columns}

    date_col = col_map.get("start date") or col_map.get("date") or None
    if date_col is None:
        sig = _empty_signal("date column missing")
        _save_cached(ticker, sig)
        return sig

    df[date_col] = pd.to_datetime(df[date_col], errors="coerce", utc=True)
    cutoff = pd.Timestamp.now(tz="UTC") - pd.Timedelta(days=days)
    df = df[df[date_col] >= cutoff]
    if df.empty:
        sig = _empty_signal("no recent insider activity")
        _save_cached(ticker, sig)
        return sig

    # Detect transaction type. yfinance puts text like "Purchase at price..." or
    # "Sale at price..." in the Text column.
    text_col = col_map.get("text") or col_map.get("transaction") or None
    value_col = col_map.get("value") or col_map.get("$ value") or None
    if text_col is None:
        sig = _empty_signal("transaction text missing")
        _save_cached(ticker, sig)
        return sig

    buys = df[df[text_col].astype(str).str.contains("Purchase", case=False, na=False)]
    sells = df[df[text_col].astype(str).str.contains("Sale", case=False, na=False)]

    buy_count  = int(len(buys))
    sell_count = int(len(sells))

    def _sum_dollars(sub_df):
        if value_col and value_col in sub_df.columns:
            return float(pd.to_numeric(sub_df[value_col], errors="coerce").fillna(0).sum())
        return 0.0

    buy_dollar  = _sum_dollars(buys)
    sell_dollar = _sum_dollars(sells)
    net_dollar  = buy_dollar - sell_dollar

    # Trigger = cluster of buys with meaningful dollar value, no large offsetting sells
    triggered = (
        buy_count >= _MIN_BUYS_FOR_CLUSTER
        and net_dollar >= _MIN_NET_DOLLAR
    )

    # Side: cluster of buys = bull; cluster of sells = bear (less reliable but tracked)
    if triggered:
        side = "bull"
    elif sell_count >= _MIN_BUYS_FOR_CLUSTER and net_dollar <= -_MIN_NET_DOLLAR:
        side = "bear"
        triggered = True   # bearish signal also worth surfacing
    else:
        side = "neutral"

    # Strength: scale by dollar size (capped). $1M+ net = full strength.
    strength = min(1.0, abs(net_dollar) / 1_000_000)

    if triggered and side == "bull":
        summary = f"Insider cluster buy ({buy_count} buys, +${buy_dollar/1000:.0f}k net)"
    elif triggered and side == "bear":
        summary = f"Insider cluster sell ({sell_count} sells, -${abs(net_dollar)/1000:.0f}k net)"
    else:
        summary = ""

    sig = {
        "triggered":   bool(triggered),
        "buy_count":   buy_count,
        "sell_count":  sell_count,
        "buy_dollar":  buy_dollar,
        "sell_dollar": sell_dollar,
        "net_dollar":  net_dollar,
        "side":        side,
        "strength":    round(strength, 3),
        "summary":     summary,
    }
    _save_cached(ticker, sig)
    return sig
