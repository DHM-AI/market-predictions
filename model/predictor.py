import os
import json
import pickle
import pandas as pd
import numpy as np
from signals.technicals import compute_feature_row
from signals.sentiment import normalize_score
from signals.scorer import score_universe as rule_score_universe
from config import MODEL_PATH, FEATURE_NAMES_PATH, XGB_WEIGHT, SENTIMENT_WEIGHT, MIN_SCORE_TO_ALERT

_model = None
_feature_names: list[str] = []


def _load_model():
    global _model, _feature_names
    if _model is not None:
        return _model
    if not os.path.exists(MODEL_PATH):
        return None
    with open(MODEL_PATH, "rb") as f:
        _model = pickle.load(f)
    if os.path.exists(FEATURE_NAMES_PATH):
        with open(FEATURE_NAMES_PATH) as f:
            _feature_names = json.load(f)
    return _model


def model_available() -> bool:
    return os.path.exists(MODEL_PATH)


def _xgb_prob(df: pd.DataFrame) -> float:
    model = _load_model()
    if model is None or df.empty:
        return 0.0
    try:
        if not _feature_names:
            return 0.0
        features = compute_feature_row(df)
        row = [features.get(col, 0.0) for col in _feature_names]
        X = np.array(row).reshape(1, -1)
        prob = float(model.predict_proba(X)[0][1])
        return max(0.0, min(1.0, prob))
    except Exception:
        return 0.0


def predict_universe(
    tickers: list[str],
    ohlcv_map: dict[str, pd.DataFrame],
    sentiment_map: dict[str, dict] | None = None,
    earnings_map: dict[str, int | None] | None = None,
) -> pd.DataFrame:
    """
    Score all tickers. Uses XGBoost if model is trained, otherwise falls back
    to rule-based scorer. Blends XGB probability with live sentiment.
    """
    use_xgb = model_available()

    if not use_xgb:
        print("[predictor] No trained model found — using rule-based scorer.")
        return rule_score_universe(tickers, ohlcv_map, sentiment_map, earnings_map)

    from signals.scorer import score_ticker  # for direction/duration/signals logic
    rows = []
    for ticker in tickers:
        df = ohlcv_map.get(ticker, pd.DataFrame())
        sentiment = (sentiment_map or {}).get(ticker, {})
        earnings = (earnings_map or {}).get(ticker)

        if df is None or df.empty:
            continue

        # Get XGB probability (0-1)
        xgb_prob = _xgb_prob(df)

        # Normalize sentiment score to 0-1, clamped to prevent overflow
        sent_score_norm = max(0.0, min(1.0, normalize_score(sentiment.get("score", 0.0))))

        # Blend: weighted average → 0-100 scale
        blended = (XGB_WEIGHT * xgb_prob + SENTIMENT_WEIGHT * sent_score_norm) * 100

        if blended < MIN_SCORE_TO_ALERT:
            continue

        # Re-use rule scorer for direction/duration/signals labels (no re-fetch)
        meta = score_ticker(ticker, df, sentiment, earnings)
        meta["score"] = round(blended, 1)
        meta["xgb_prob"] = round(xgb_prob, 4)
        rows.append(meta)

    if not rows:
        return pd.DataFrame()

    result = pd.DataFrame(rows).sort_values("score", ascending=False).reset_index(drop=True)
    return result
