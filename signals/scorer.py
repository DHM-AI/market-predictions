import pandas as pd
from signals.technicals import compute_all
from signals.sentiment import get_sentiment_with_velocity, normalize_score
from data.fetcher import get_earnings_days
from config import WEIGHTS, EARNINGS_PROXIMITY_DAYS, MIN_SCORE_TO_ALERT


def _determine_direction(technicals: dict, sentiment: dict) -> str:
    votes_bull = 0
    votes_bear = 0

    rsi = technicals["rsi"]
    if rsi["side"] == "bull":
        votes_bull += 1
    elif rsi["side"] == "bear":
        votes_bear += 1

    ema_pct = technicals["ema"]["ema50_pct"]
    if ema_pct > 2:
        votes_bull += 1
    elif ema_pct < -2:
        votes_bear += 1

    sent_score = sentiment.get("score", 0.0)
    if sent_score > 0.1:
        votes_bull += 1
    elif sent_score < -0.1:
        votes_bear += 1

    if votes_bull > votes_bear:
        return "bullish"
    if votes_bear > votes_bull:
        return "bearish"
    return "mixed"


def _determine_duration(technicals: dict, earnings_days: int | None) -> str:
    if earnings_days is not None and 0 <= earnings_days <= EARNINGS_PROXIMITY_DAYS:
        return "1-3d (earnings catalyst)"
    bb = technicals["bb"]["triggered"]
    atr = technicals["atr"]["triggered"]
    if bb and atr:
        return "5-7d (squeeze setup)"
    rsi_extreme = technicals["rsi"]["extreme"]
    vol_surge = technicals["vol"]["triggered"]
    if rsi_extreme and vol_surge:
        return "2-3w (momentum surge)"
    return "5-7d (default)"


def _determine_confidence(score: float) -> str:
    if score >= 70:
        return "High"
    if score >= 50:
        return "Medium"
    return "Low"


def score_ticker(
    ticker: str,
    ohlcv_df: pd.DataFrame,
    sentiment: dict | None = None,
    earnings_days: int | None = None,
) -> dict:
    if ohlcv_df is None or ohlcv_df.empty:
        return {"ticker": ticker, "score": 0, "error": "no data"}

    technicals = compute_all(ohlcv_df)
    if sentiment is None:
        sentiment = get_sentiment_with_velocity(ticker)

    signals_triggered = []
    breakdown = {}
    raw_score = 0

    # BB squeeze
    if technicals["bb"]["triggered"]:
        raw_score += WEIGHTS["bb_squeeze"]
        breakdown["bb_squeeze"] = WEIGHTS["bb_squeeze"]
        signals_triggered.append(f"BB squeeze (pct={technicals['bb']['width_percentile']})")
    else:
        breakdown["bb_squeeze"] = 0

    # ATR compression
    if technicals["atr"]["triggered"]:
        raw_score += WEIGHTS["atr_compression"]
        breakdown["atr_compression"] = WEIGHTS["atr_compression"]
        signals_triggered.append(f"ATR compression (ratio={technicals['atr']['ratio']})")
    else:
        breakdown["atr_compression"] = 0

    # Volume surge
    if technicals["vol"]["triggered"]:
        raw_score += WEIGHTS["volume_surge"]
        breakdown["volume_surge"] = WEIGHTS["volume_surge"]
        signals_triggered.append(f"Volume surge ({technicals['vol']['ratio']}x avg)")
    else:
        breakdown["volume_surge"] = 0

    # Sentiment spike
    if sentiment.get("spike", False):
        raw_score += WEIGHTS["sentiment_spike"]
        breakdown["sentiment_spike"] = WEIGHTS["sentiment_spike"]
        signals_triggered.append(f"Sentiment spike (Δ={sentiment.get('velocity', 0):.2f})")
    else:
        breakdown["sentiment_spike"] = 0

    # RSI extreme
    if technicals["rsi"]["extreme"]:
        raw_score += WEIGHTS["rsi_extreme"]
        breakdown["rsi_extreme"] = WEIGHTS["rsi_extreme"]
        signals_triggered.append(f"RSI extreme ({technicals['rsi']['value']})")
    else:
        breakdown["rsi_extreme"] = 0

    # Earnings proximity
    if earnings_days is not None and 0 <= earnings_days <= EARNINGS_PROXIMITY_DAYS:
        raw_score += WEIGHTS["earnings_proximity"]
        breakdown["earnings_proximity"] = WEIGHTS["earnings_proximity"]
        signals_triggered.append(f"Earnings in {earnings_days}d")
    else:
        breakdown["earnings_proximity"] = 0

    direction = _determine_direction(technicals, sentiment)
    duration = _determine_duration(technicals, earnings_days)
    confidence = _determine_confidence(raw_score)

    return {
        "ticker": ticker,
        "score": raw_score,
        "direction": direction,
        "duration": duration,
        "confidence": confidence,
        "signals_triggered": signals_triggered,
        "breakdown": breakdown,
        "rsi": technicals["rsi"]["value"],
        "bb_pct": technicals["bb"]["width_percentile"],
        "atr_ratio": technicals["atr"]["ratio"],
        "volume_ratio": technicals["vol"]["ratio"],
        "ema50_pct": technicals["ema"]["ema50_pct"],
        "sentiment_score": sentiment.get("score", 0.0),
        "sentiment_velocity": sentiment.get("velocity", 0.0),
        "earnings_days": earnings_days,
    }


def score_universe(
    tickers: list[str],
    ohlcv_map: dict[str, pd.DataFrame],
    sentiment_map: dict[str, dict] | None = None,
    earnings_map: dict[str, int | None] | None = None,
    min_score: int = MIN_SCORE_TO_ALERT,
) -> pd.DataFrame:
    rows = []
    for ticker in tickers:
        df = ohlcv_map.get(ticker, pd.DataFrame())
        sentiment = (sentiment_map or {}).get(ticker)
        earnings = (earnings_map or {}).get(ticker)
        result = score_ticker(ticker, df, sentiment, earnings)
        if result.get("score", 0) >= min_score:
            rows.append(result)
    if not rows:
        return pd.DataFrame()
    scored = pd.DataFrame(rows).sort_values("score", ascending=False).reset_index(drop=True)
    return scored
