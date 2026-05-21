"""
Market Regime Detection — prevents trading against the tape.

The single biggest reason systematic strategies blow up is ignoring macro context.
This module checks 3 independent sources and returns an overall market regime.

Checks (all free, via yfinance):
  1. VIX level   — "fear gauge"; high VIX = volatile, dangerous
  2. SPY trend   — price vs 50 / 200 MA; below = bear tape
  3. Sector breadth — how many of 11 sector ETFs are above their 50 MA

Regime → auto-execution behavior:
  bull    → full normal operation
  neutral → reduce bullish position sizes by 20%, bearish fine
  bear    → reduce bullish by 40%, stop auto-exec if VIX extreme
"""

import yfinance as yf
import pandas as pd
from datetime import datetime

# 11 GICS sector ETFs
SECTOR_ETFS = ["XLK","XLF","XLE","XLV","XLY","XLI","XLB","XLRE","XLU","XLP","XLC"]

VIX_LOW      = 15    # calm market
VIX_ELEVATED = 25    # start being cautious
VIX_HIGH     = 35    # significantly reduce risk
VIX_EXTREME  = 45    # halt bullish auto-execution

_cache: dict = {}
_cache_ts: datetime | None = None
CACHE_MINUTES = 30


def _is_cache_fresh() -> bool:
    if _cache_ts is None:
        return False
    return (datetime.now() - _cache_ts).total_seconds() < CACHE_MINUTES * 60


def get_market_regime(force_refresh: bool = False) -> dict:
    """
    Returns market regime dict. Cached for 30 minutes.

    Returns:
        regime              "bull" | "neutral" | "bear"
        vix                 float — current VIX value
        vix_level           "low" | "normal" | "elevated" | "high" | "extreme"
        spy_vs_200ma_pct    % SPY is above/below its 200 MA
        spy_vs_50ma_pct     % SPY is above/below its 50 MA
        spy_trend           "uptrend" | "sideways" | "downtrend"
        sectors_above_50ma  int (0-11)
        breadth             "strong" | "normal" | "weak"
        bull_multiplier     float — multiply bullish scores by this (1.0 = unchanged)
        auto_exec_ok        bool — whether to allow new auto-executions
        warning             str | None — human-readable warning
    """
    global _cache, _cache_ts

    if not force_refresh and _is_cache_fresh() and _cache:
        return _cache

    result = _fetch_regime()
    _cache    = result
    _cache_ts = datetime.now()
    return result


def _fetch_regime() -> dict:
    try:
        # ── VIX ──────────────────────────────────────────────────────────────
        vix_df = yf.download("^VIX", period="5d", interval="1d",
                             progress=False, auto_adjust=True)
        if isinstance(vix_df.columns, pd.MultiIndex):
            vix_df.columns = vix_df.columns.get_level_values(0)
        vix = float(vix_df["Close"].iloc[-1]) if not vix_df.empty else 20.0

        if vix < VIX_LOW:
            vix_level = "low"
        elif vix < VIX_ELEVATED:
            vix_level = "normal"
        elif vix < VIX_HIGH:
            vix_level = "elevated"
        elif vix < VIX_EXTREME:
            vix_level = "high"
        else:
            vix_level = "extreme"

        # ── SPY trend (50 / 200 MA) ───────────────────────────────────────────
        spy_df = yf.download("SPY", period="1y", interval="1d",
                             progress=False, auto_adjust=True)
        if isinstance(spy_df.columns, pd.MultiIndex):
            spy_df.columns = spy_df.columns.get_level_values(0)

        spy_close = float(spy_df["Close"].iloc[-1]) if not spy_df.empty else 500.0
        spy_ma50  = float(spy_df["Close"].rolling(50).mean().dropna().iloc[-1])  if len(spy_df) >= 50  else spy_close
        spy_ma200 = float(spy_df["Close"].rolling(200).mean().dropna().iloc[-1]) if len(spy_df) >= 200 else spy_close
        if spy_ma50  != spy_ma50:  spy_ma50  = spy_close   # NaN guard
        if spy_ma200 != spy_ma200: spy_ma200 = spy_close   # NaN guard

        spy_vs_50ma_pct  = round((spy_close / spy_ma50  - 1) * 100, 2)
        spy_vs_200ma_pct = round((spy_close / spy_ma200 - 1) * 100, 2)

        if spy_vs_200ma_pct > 2 and spy_vs_50ma_pct > 0:
            spy_trend = "uptrend"
        elif spy_vs_200ma_pct < -5:
            spy_trend = "downtrend"
        else:
            spy_trend = "sideways"

        # ── Sector breadth ────────────────────────────────────────────────────
        sectors_above = 0
        try:
            etf_data = yf.download(SECTOR_ETFS, period="3mo", interval="1d",
                                   progress=False, auto_adjust=True, group_by="ticker")
            for etf in SECTOR_ETFS:
                try:
                    s = etf_data[etf]["Close"] if isinstance(etf_data.columns, pd.MultiIndex) else etf_data["Close"]
                    if len(s.dropna()) >= 50:
                        price = float(s.dropna().iloc[-1])
                        ma50  = float(s.dropna().rolling(50).mean().iloc[-1])
                        if price > ma50:
                            sectors_above += 1
                except Exception:
                    pass
        except Exception:
            sectors_above = 6   # assume neutral if fetch fails

        if sectors_above >= 7:
            breadth = "strong"
        elif sectors_above >= 4:
            breadth = "normal"
        else:
            breadth = "weak"

        # ── Overall regime ────────────────────────────────────────────────────
        bull_points  = 0
        bear_points  = 0

        # VIX contribution
        if vix_level in ("low", "normal"):
            bull_points += 1
        elif vix_level in ("high", "extreme"):
            bear_points += 2
        else:
            bear_points += 1

        # SPY trend contribution
        if spy_trend == "uptrend":
            bull_points += 2
        elif spy_trend == "downtrend":
            bear_points += 2
        else:
            bull_points += 1

        # Breadth contribution
        if breadth == "strong":
            bull_points += 1
        elif breadth == "weak":
            bear_points += 1

        if bull_points >= 3 and bear_points <= 1:
            regime = "bull"
        elif bear_points >= 3:
            regime = "bear"
        else:
            regime = "neutral"

        # ── Multipliers & gates ───────────────────────────────────────────────
        if regime == "bull" and vix_level in ("low", "normal"):
            bull_multiplier = 1.0
        elif regime == "neutral" or vix_level == "elevated":
            bull_multiplier = 0.80
        elif regime == "bear" or vix_level == "high":
            bull_multiplier = 0.60
        else:
            bull_multiplier = 0.40   # extreme VIX

        auto_exec_ok = vix_level != "extreme" and regime != "bear"

        # ── Warning text ──────────────────────────────────────────────────────
        warnings = []
        if vix_level in ("high", "extreme"):
            warnings.append(f"VIX {vix:.0f} — extreme fear, position sizes reduced")
        if spy_trend == "downtrend":
            warnings.append(f"SPY {spy_vs_200ma_pct:+.1f}% vs 200MA — bear tape")
        if breadth == "weak":
            warnings.append(f"Only {sectors_above}/11 sectors above 50MA — weak breadth")
        if not auto_exec_ok:
            warnings.append("Auto-execution PAUSED for bullish setups")

        warning = " · ".join(warnings) if warnings else None

        return {
            "regime":            regime,
            "vix":               round(vix, 1),
            "vix_level":         vix_level,
            "spy_vs_200ma_pct":  spy_vs_200ma_pct,
            "spy_vs_50ma_pct":   spy_vs_50ma_pct,
            "spy_trend":         spy_trend,
            "sectors_above_50ma": sectors_above,
            "breadth":           breadth,
            "bull_multiplier":   round(bull_multiplier, 2),
            "auto_exec_ok":      auto_exec_ok,
            "warning":           warning,
        }

    except Exception as e:
        print(f"[regime] Error fetching regime: {e}")
        return {
            "regime":            "neutral",
            "vix":               20.0,
            "vix_level":         "normal",
            "spy_vs_200ma_pct":  0.0,
            "spy_vs_50ma_pct":   0.0,
            "spy_trend":         "sideways",
            "sectors_above_50ma": 5,
            "breadth":           "normal",
            "bull_multiplier":   1.0,
            "auto_exec_ok":      True,
            "warning":           f"Regime check failed: {e}",
        }
