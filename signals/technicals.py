import pandas as pd
import numpy as np
import pandas_ta as ta
from config import BB_SQUEEZE_PERCENTILE, ATR_COMPRESSION_RATIO, VOLUME_SURGE_RATIO, RSI_OVERBOUGHT, RSI_OVERSOLD


def _require_min_rows(df: pd.DataFrame, n: int) -> bool:
    return len(df) >= n


def bb_squeeze(df: pd.DataFrame, window: int = 50) -> dict:
    if not _require_min_rows(df, window + 20):
        return {"triggered": False, "width_percentile": 50.0, "width": None}
    try:
        bbands = ta.bbands(df["Close"], length=20)
        if bbands is None or bbands.empty:
            return {"triggered": False, "width_percentile": 50.0, "width": None}
        upper_col = [c for c in bbands.columns if "BBU" in c][0]
        lower_col = [c for c in bbands.columns if "BBL" in c][0]
        mid_col = [c for c in bbands.columns if "BBM" in c][0]
        width = (bbands[upper_col] - bbands[lower_col]) / bbands[mid_col]
        width = width.dropna()
        if len(width) < window:
            return {"triggered": False, "width_percentile": 50.0, "width": None}
        current = width.iloc[-1]
        rolling_window = width.iloc[-window:]
        pct = float(pd.Series(rolling_window).rank(pct=True).iloc[-1] * 100)
        triggered = pct <= BB_SQUEEZE_PERCENTILE
        return {"triggered": triggered, "width_percentile": round(pct, 1), "width": round(float(current), 4)}
    except Exception:
        return {"triggered": False, "width_percentile": 50.0, "width": None}


def atr_compression(df: pd.DataFrame, atr_period: int = 14, avg_period: int = 50) -> dict:
    if not _require_min_rows(df, avg_period + atr_period):
        return {"triggered": False, "ratio": 1.0}
    try:
        atr = ta.atr(df["High"], df["Low"], df["Close"], length=atr_period).dropna()
        if len(atr) < avg_period:
            return {"triggered": False, "ratio": 1.0}
        current_atr = float(atr.iloc[-1])
        avg_atr = float(atr.iloc[-avg_period:].mean())
        if avg_atr == 0:
            return {"triggered": False, "ratio": 1.0}
        ratio = current_atr / avg_atr
        return {"triggered": ratio < ATR_COMPRESSION_RATIO, "ratio": round(ratio, 3)}
    except Exception:
        return {"triggered": False, "ratio": 1.0}


def volume_surge(df: pd.DataFrame, avg_period: int = 20) -> dict:
    if not _require_min_rows(df, avg_period + 1):
        return {"triggered": False, "ratio": 1.0}
    try:
        vol = df["Volume"].dropna()
        if len(vol) < avg_period + 1:
            return {"triggered": False, "ratio": 1.0}
        today_vol = float(vol.iloc[-1])
        avg_vol = float(vol.iloc[-(avg_period + 1):-1].mean())
        if avg_vol == 0:
            return {"triggered": False, "ratio": 1.0}
        ratio = today_vol / avg_vol
        return {"triggered": ratio >= VOLUME_SURGE_RATIO, "ratio": round(ratio, 2)}
    except Exception:
        return {"triggered": False, "ratio": 1.0}


def rsi_signal(df: pd.DataFrame, period: int = 14) -> dict:
    if not _require_min_rows(df, period + 5):
        return {"value": 50.0, "extreme": False, "side": "neutral"}
    try:
        rsi = ta.rsi(df["Close"], length=period).dropna()
        if rsi.empty:
            return {"value": 50.0, "extreme": False, "side": "neutral"}
        val = float(rsi.iloc[-1])
        if val >= RSI_OVERBOUGHT:
            return {"value": round(val, 1), "extreme": True, "side": "bull"}
        if val <= RSI_OVERSOLD:
            return {"value": round(val, 1), "extreme": True, "side": "bear"}
        return {"value": round(val, 1), "extreme": False, "side": "neutral"}
    except Exception:
        return {"value": 50.0, "extreme": False, "side": "neutral"}


def price_vs_ema(df: pd.DataFrame, period: int = 50) -> dict:
    if not _require_min_rows(df, period):
        return {"ema50_pct": 0.0}
    try:
        ema = ta.ema(df["Close"], length=period).dropna()
        if ema.empty:
            return {"ema50_pct": 0.0}
        ema_val = float(ema.iloc[-1])
        price = float(df["Close"].iloc[-1])
        pct = (price - ema_val) / ema_val * 100
        return {"ema50_pct": round(pct, 2)}
    except Exception:
        return {"ema50_pct": 0.0}


def compute_all(df: pd.DataFrame) -> dict:
    return {
        "bb": bb_squeeze(df),
        "atr": atr_compression(df),
        "vol": volume_surge(df),
        "rsi": rsi_signal(df),
        "ema": price_vs_ema(df),
    }


def compute_feature_row(df: pd.DataFrame) -> dict:
    """Return a flat feature dict suitable for ML training/inference."""
    bb = bb_squeeze(df)
    atr = atr_compression(df)
    vol = volume_surge(df)
    rsi = rsi_signal(df)
    ema = price_vs_ema(df)
    return {
        "bb_width_pct": bb["width_percentile"],
        "bb_squeeze": int(bb["triggered"]),
        "atr_ratio": atr["ratio"],
        "atr_compression": int(atr["triggered"]),
        "volume_ratio": vol["ratio"],
        "volume_surge": int(vol["triggered"]),
        "rsi_value": rsi["value"],
        "rsi_extreme": int(rsi["extreme"]),
        "rsi_bull": int(rsi["side"] == "bull"),
        "rsi_bear": int(rsi["side"] == "bear"),
        "ema50_pct": ema["ema50_pct"],
    }
