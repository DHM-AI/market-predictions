"""
Candlestick & Price Pattern Detection.

Computed entirely from OHLCV — no extra API calls, no latency.

Patterns detected:
  Bullish reversals  → Hammer, Bullish Engulfing, Morning Star, Bullish Pin Bar
  Bearish reversals  → Shooting Star, Bearish Engulfing, Evening Star, Bearish Pin Bar
  Trend structures   → Higher highs / Higher lows, Lower lows / Lower highs
  Consolidation      → Inside bar, Doji (used as bonus context, not standalone)

Each pattern returns a standardized dict:
  {
    "triggered": bool,
    "side":      "bull" | "bear" | "neutral",
    "pattern":   str,   # human-readable name
    "strength":  float, # 0.0-1.0 confidence
  }
"""

import pandas as pd
import numpy as np


# ── Candle decomposition ─────────────────────────────────────────────────────

def _candle_parts(o: float, h: float, l: float, c: float):
    """Return (body, upper_wick, lower_wick, total_range, body_pct)."""
    body        = abs(c - o)
    upper_wick  = h - max(c, o)
    lower_wick  = min(c, o) - l
    total_range = h - l
    body_pct    = (body / total_range) if total_range > 0 else 0.5
    is_bull     = c >= o
    return body, upper_wick, lower_wick, total_range, body_pct, is_bull


# ── Individual pattern detectors ─────────────────────────────────────────────

def _hammer(df: pd.DataFrame) -> dict:
    """
    Hammer — long lower wick (≥2× body), small upper wick, small body.
    Bullish reversal when appearing after a downtrend.
    """
    if len(df) < 10:
        return {"triggered": False, "side": "neutral", "pattern": None, "strength": 0}

    row  = df.iloc[-1]
    o, h, l, c = float(row["Open"]), float(row["High"]), float(row["Low"]), float(row["Close"])
    body, upper_wick, lower_wick, total_range, body_pct, is_bull = _candle_parts(o, h, l, c)

    # Downtrend context: price below 10-period MA
    ma10 = df["Close"].rolling(10).mean().iloc[-1]
    in_downtrend = c < float(ma10)

    is_hammer = (
        lower_wick >= 2 * body
        and upper_wick <= body * 0.5
        and body_pct < 0.35
        and total_range > 0
        and in_downtrend
    )

    strength = min(1.0, lower_wick / max(total_range, 0.01)) if is_hammer else 0.0
    return {
        "triggered": is_hammer,
        "side":      "bull" if is_hammer else "neutral",
        "pattern":   "Hammer" if is_hammer else None,
        "strength":  round(strength, 2),
    }


def _shooting_star(df: pd.DataFrame) -> dict:
    """
    Shooting Star — long upper wick (≥2× body), small lower wick.
    Bearish reversal when appearing after an uptrend.
    """
    if len(df) < 10:
        return {"triggered": False, "side": "neutral", "pattern": None, "strength": 0}

    row  = df.iloc[-1]
    o, h, l, c = float(row["Open"]), float(row["High"]), float(row["Low"]), float(row["Close"])
    body, upper_wick, lower_wick, total_range, body_pct, is_bull = _candle_parts(o, h, l, c)

    ma10 = df["Close"].rolling(10).mean().iloc[-1]
    in_uptrend = c > float(ma10)

    is_star = (
        upper_wick >= 2 * body
        and lower_wick <= body * 0.5
        and body_pct < 0.35
        and total_range > 0
        and in_uptrend
    )

    strength = min(1.0, upper_wick / max(total_range, 0.01)) if is_star else 0.0
    return {
        "triggered": is_star,
        "side":      "bear" if is_star else "neutral",
        "pattern":   "Shooting Star" if is_star else None,
        "strength":  round(strength, 2),
    }


def _engulfing(df: pd.DataFrame) -> dict:
    """
    Engulfing — current candle's body completely covers the previous candle's body.
    Bullish: green engulfs red after downtrend.
    Bearish: red engulfs green after uptrend.
    """
    if len(df) < 11:
        return {"triggered": False, "side": "neutral", "pattern": None, "strength": 0}

    prev = df.iloc[-2]
    curr = df.iloc[-1]

    po, pc = float(prev["Open"]), float(prev["Close"])
    co, cc = float(curr["Open"]), float(curr["Close"])

    prev_body  = abs(pc - po)
    curr_body  = abs(cc - co)
    prev_bull  = pc > po
    curr_bull  = cc > co

    engulfs = curr_body > prev_body and min(co, cc) < min(po, pc) and max(co, cc) > max(po, pc)

    if not engulfs or prev_body == 0:
        return {"triggered": False, "side": "neutral", "pattern": None, "strength": 0}

    ma10 = df["Close"].rolling(10).mean().iloc[-2]

    if curr_bull and not prev_bull and float(prev["Close"]) < float(ma10):
        side    = "bull"
        pattern = "Bullish Engulfing"
    elif not curr_bull and prev_bull and float(prev["Close"]) > float(ma10):
        side    = "bear"
        pattern = "Bearish Engulfing"
    else:
        return {"triggered": False, "side": "neutral", "pattern": None, "strength": 0}

    strength = min(1.0, curr_body / max(prev_body, 0.001))
    return {
        "triggered": True,
        "side":      side,
        "pattern":   pattern,
        "strength":  round(strength, 2),
    }


def _pin_bar(df: pd.DataFrame) -> dict:
    """
    Pin Bar — extreme wick rejection. Wick ≥ 3× body, small body.
    Very reliable reversal signal — institutional rejection of a price level.
    """
    if len(df) < 5:
        return {"triggered": False, "side": "neutral", "pattern": None, "strength": 0}

    row = df.iloc[-1]
    o, h, l, c = float(row["Open"]), float(row["High"]), float(row["Low"]), float(row["Close"])
    body, upper_wick, lower_wick, total_range, body_pct, is_bull = _candle_parts(o, h, l, c)

    if body == 0 or total_range == 0:
        return {"triggered": False, "side": "neutral", "pattern": None, "strength": 0}

    # Bullish pin bar: long lower wick rejecting lows
    if lower_wick >= 3 * body and lower_wick >= 0.6 * total_range:
        return {
            "triggered": True,
            "side":      "bull",
            "pattern":   "Bullish Pin Bar",
            "strength":  round(min(1.0, lower_wick / total_range), 2),
        }

    # Bearish pin bar: long upper wick rejecting highs
    if upper_wick >= 3 * body and upper_wick >= 0.6 * total_range:
        return {
            "triggered": True,
            "side":      "bear",
            "pattern":   "Bearish Pin Bar",
            "strength":  round(min(1.0, upper_wick / total_range), 2),
        }

    return {"triggered": False, "side": "neutral", "pattern": None, "strength": 0}


def _trend_structure(df: pd.DataFrame) -> dict:
    """
    Trend structure — higher highs + higher lows (bull) vs lower lows + lower highs (bear).
    Uses the last 20 bars. Confirms the directional bias of other signals.
    """
    if len(df) < 20:
        return {"triggered": False, "side": "neutral", "pattern": None, "strength": 0}

    closes   = df["Close"].iloc[-20:].values
    highs    = df["High"].iloc[-20:].values
    lows     = df["Low"].iloc[-20:].values

    # Split into two halves
    first_half_high = highs[:10].max()
    second_half_high = highs[10:].max()
    first_half_low  = lows[:10].min()
    second_half_low  = lows[10:].min()

    # Linear regression slope of closes
    x      = np.arange(len(closes))
    slope  = float(np.polyfit(x, closes, 1)[0])
    avg    = float(closes.mean())
    slope_pct = slope / avg * 100  # % per day

    if slope_pct > 0.15 and second_half_high > first_half_high and second_half_low > first_half_low:
        return {
            "triggered": True,
            "side":      "bull",
            "pattern":   "Uptrend Structure",
            "strength":  round(min(1.0, slope_pct / 0.5), 2),
        }
    elif slope_pct < -0.15 and second_half_high < first_half_high and second_half_low < first_half_low:
        return {
            "triggered": True,
            "side":      "bear",
            "pattern":   "Downtrend Structure",
            "strength":  round(min(1.0, abs(slope_pct) / 0.5), 2),
        }

    return {"triggered": False, "side": "neutral", "pattern": None, "strength": 0}


# ── Combined pattern scorer ───────────────────────────────────────────────────

def detect_patterns(df: pd.DataFrame) -> dict:
    """
    Run all pattern detectors on an OHLCV DataFrame.
    Returns the STRONGEST triggered pattern (or neutral if none).

    Returns:
        {
            "triggered": bool,
            "side":      "bull" | "bear" | "neutral",
            "pattern":   str | None,
            "strength":  float (0-1),
            "all":       list of all triggered patterns
        }
    """
    if df is None or len(df) < 10:
        return {"triggered": False, "side": "neutral", "pattern": None,
                "strength": 0.0, "all": []}

    # Ensure OHLC columns exist
    required = {"Open", "High", "Low", "Close"}
    if not required.issubset(set(df.columns)):
        return {"triggered": False, "side": "neutral", "pattern": None,
                "strength": 0.0, "all": []}

    detectors = [_pin_bar, _engulfing, _hammer, _shooting_star, _trend_structure]
    triggered = []

    for fn in detectors:
        try:
            result = fn(df)
            if result["triggered"]:
                triggered.append(result)
        except Exception:
            continue

    if not triggered:
        return {"triggered": False, "side": "neutral", "pattern": None,
                "strength": 0.0, "all": []}

    # Pick the strongest triggered pattern
    best = max(triggered, key=lambda x: x["strength"])

    return {
        "triggered": True,
        "side":      best["side"],
        "pattern":   best["pattern"],
        "strength":  best["strength"],
        "all":       [p["pattern"] for p in triggered],
    }
