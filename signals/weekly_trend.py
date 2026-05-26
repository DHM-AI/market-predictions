from __future__ import annotations
"""
Weekly trend signal — multi-timeframe alignment check.

Daily charts are noisy. The weekly chart filters out news blips and algo wash.
If the daily signal is screaming "buy" but the weekly is in a clear downtrend,
the daily move is most likely a dead-cat bounce.

Three checks (all must align for a clean bullish/bearish read):
    1. Price above 20-week MA          (medium-term trend)
    2. Price above 50-week MA          (long-term trend)
    3. Higher high over the last 5wk   (no breakdown)

Public API:
    get_weekly_trend(ticker, ohlcv_df=None) -> dict
        Returns:
          {
            "trend":          "bullish" | "bearish" | "neutral",
            "above_20wma":    bool,
            "above_50wma":    bool,
            "higher_highs":   bool,
            "strength":       float,    # 0..1
            "summary":        str,
          }

If ohlcv_df is passed (daily OHLCV the scorer already has), we resample
to weekly to avoid a second yfinance call per ticker. Otherwise we fetch
2 years of weekly data via yfinance.
"""
from datetime import datetime, timedelta, timezone
import json

import pandas as pd
import yfinance as yf


_CACHE_HOURS = 6   # weekly data doesn't change often
_HIGHER_HIGH_LOOKBACK = 5   # weeks


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
        res = (client.table("weekly_trend_cache")
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
        client.table("weekly_trend_cache").upsert({
            "ticker":     ticker,
            "checked_at": datetime.now(timezone.utc).isoformat(),
            "payload":    payload,
        }, on_conflict="ticker").execute()
    except Exception:
        pass


def _empty(reason: str = "") -> dict:
    return {
        "trend":        "neutral",
        "above_20wma":  False,
        "above_50wma":  False,
        "higher_highs": False,
        "strength":     0.0,
        "summary":      reason,
    }


def _resample_to_weekly(daily_df: pd.DataFrame) -> pd.DataFrame:
    """Resample daily OHLCV to weekly bars (Mon–Fri)."""
    if daily_df is None or daily_df.empty:
        return pd.DataFrame()
    df = daily_df.copy()
    if not isinstance(df.index, pd.DatetimeIndex):
        df.index = pd.to_datetime(df.index)
    weekly = df.resample("W-FRI").agg({
        "Open":  "first",
        "High":  "max",
        "Low":   "min",
        "Close": "last",
        "Volume":"sum",
    }).dropna()
    return weekly


def get_weekly_trend(ticker: str, ohlcv_df: pd.DataFrame | None = None) -> dict:
    """Compute weekly trend alignment. Returns cached result if fresh."""
    if not ticker:
        return _empty()

    cached = _load_cached(ticker)
    if cached is not None:
        return cached

    # Prefer resampling the daily OHLCV the scorer already has — avoids a 2nd API call.
    weekly = pd.DataFrame()
    if ohlcv_df is not None and not ohlcv_df.empty and len(ohlcv_df) >= 250:
        weekly = _resample_to_weekly(ohlcv_df)

    if weekly.empty or len(weekly) < 50:
        # Fall back to direct yfinance weekly fetch
        try:
            weekly = yf.download(
                ticker, period="2y", interval="1wk",
                progress=False, auto_adjust=True,
            )
            if isinstance(weekly.columns, pd.MultiIndex):
                weekly.columns = weekly.columns.get_level_values(0)
            weekly = weekly.dropna(how="all")
        except Exception as e:
            return _empty(f"weekly fetch failed: {e}")

    if weekly.empty or len(weekly) < 50:
        sig = _empty("not enough weekly history")
        _save_cached(ticker, sig)
        return sig

    closes = weekly["Close"]
    highs  = weekly["High"]

    wma20 = closes.rolling(20).mean()
    wma50 = closes.rolling(50).mean()

    last_close = float(closes.iloc[-1])
    last_wma20 = float(wma20.iloc[-1]) if not pd.isna(wma20.iloc[-1]) else None
    last_wma50 = float(wma50.iloc[-1]) if not pd.isna(wma50.iloc[-1]) else None

    if last_wma20 is None or last_wma50 is None:
        sig = _empty("MA not yet defined")
        _save_cached(ticker, sig)
        return sig

    above_20 = last_close > last_wma20
    above_50 = last_close > last_wma50

    # Higher-high check: latest high > high from N weeks ago
    if len(highs) > _HIGHER_HIGH_LOOKBACK:
        higher_highs = float(highs.iloc[-1]) > float(highs.iloc[-1 - _HIGHER_HIGH_LOOKBACK])
    else:
        higher_highs = False

    # Symmetrical for bearish: below both MAs + lower lows
    lows = weekly["Low"]
    if len(lows) > _HIGHER_HIGH_LOOKBACK:
        lower_lows = float(lows.iloc[-1]) < float(lows.iloc[-1 - _HIGHER_HIGH_LOOKBACK])
    else:
        lower_lows = False

    if above_20 and above_50 and higher_highs:
        trend = "bullish"
        strength = 1.0
    elif above_20 and above_50:
        trend = "bullish"
        strength = 0.6   # MAs aligned but momentum stalling
    elif (not above_20) and (not above_50) and lower_lows:
        trend = "bearish"
        strength = 1.0
    elif (not above_20) and (not above_50):
        trend = "bearish"
        strength = 0.6
    else:
        trend = "neutral"
        strength = 0.0

    # Human summary
    if trend == "bullish":
        summary = f"Weekly uptrend (close above {'both MAs' if above_50 else '20wma'})"
    elif trend == "bearish":
        summary = f"Weekly downtrend (close below {'both MAs' if not above_50 else '20wma'})"
    else:
        summary = "Weekly mixed"

    sig = {
        "trend":        trend,
        "above_20wma":  bool(above_20),
        "above_50wma":  bool(above_50),
        "higher_highs": bool(higher_highs),
        "strength":     round(strength, 2),
        "summary":      summary,
    }
    _save_cached(ticker, sig)
    return sig


# Mode B parameters — soft booster.
# Confirming the daily direction gets a bonus; counter-trend gets a penalty
# (penalty larger than bonus because counter-trend trades are riskier).
WEEKLY_BONUS_PCT_BULL_ALIGN = 10   # picking LONG when weekly bullish, or SHORT when bearish
WEEKLY_PENALTY_PCT_COUNTER  = 15   # picking LONG when weekly bearish, or SHORT when bullish


def weekly_modifier(direction: str, weekly_trend: str, strength: float) -> int:
    """
    Return the signed score modifier to apply for a given pick direction
    and weekly trend reading.

    direction:    "bullish" | "bearish" | "mixed"
    weekly_trend: "bullish" | "bearish" | "neutral"
    strength:     0..1 (scales the bonus/penalty)

    Mode B (soft) — both bonuses and penalties are applied, never a hard veto.
    """
    if weekly_trend == "neutral":
        return 0
    aligned = (
        (direction == "bullish" and weekly_trend == "bullish")
        or (direction == "bearish" and weekly_trend == "bearish")
    )
    counter = (
        (direction == "bullish" and weekly_trend == "bearish")
        or (direction == "bearish" and weekly_trend == "bullish")
    )
    if aligned:
        return round(WEEKLY_BONUS_PCT_BULL_ALIGN * strength)
    if counter:
        return -round(WEEKLY_PENALTY_PCT_COUNTER * strength)
    return 0
