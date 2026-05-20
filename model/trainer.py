"""
Train XGBoost classifier on 3 years of S&P 500 history.

Run once before first agent scan:
    python -m model.trainer

Saves model artifacts to model/saved/.
"""
import os
import json
import pickle
import time
import numpy as np
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta
from xgboost import XGBClassifier
from sklearn.model_selection import TimeSeriesSplit
from sklearn.metrics import classification_report, roc_auc_score
from sklearn.preprocessing import StandardScaler

from data.universe import get_sp500_tickers, FUTURES
from signals.technicals import compute_feature_row
from config import TRAIN_YEARS, TRAIN_TEST_SPLIT, MOVE_TARGET_PCT, MODEL_PATH, FEATURE_NAMES_PATH

SAVE_DIR = "model/saved"
CACHE_PARQUET = "model/saved/training_data.parquet"


def _fetch_training_data(tickers: list[str], years: int = 3) -> pd.DataFrame:
    period = f"{years}y"
    print(f"[trainer] Fetching {years}y history for {len(tickers)} tickers...")
    rows = []
    chunk_size = 30

    for i in range(0, len(tickers), chunk_size):
        chunk = tickers[i:i + chunk_size]
        pct_done = i / len(tickers) * 100
        print(f"  {pct_done:.0f}% — chunk {i//chunk_size + 1}/{(len(tickers)-1)//chunk_size + 1}")
        try:
            raw = yf.download(
                chunk, period=period, interval="1d",
                progress=False, auto_adjust=True, group_by="ticker"
            )
            for ticker in chunk:
                try:
                    if len(chunk) == 1:
                        df = raw.copy()
                        if isinstance(df.columns, pd.MultiIndex):
                            df.columns = df.columns.get_level_values(0)
                    else:
                        df = raw[ticker].copy()
                    df = df.dropna(how="all")
                    if df.empty or len(df) < 80:
                        continue
                    df.index = pd.to_datetime(df.index)

                    # Compute features and labels for each row
                    for idx in range(60, len(df) - 6):
                        window = df.iloc[:idx + 1]
                        try:
                            features = compute_feature_row(window)
                        except Exception:
                            continue

                        # Label: did price move ±5% in next 5 days?
                        future = df["Close"].iloc[idx + 1:idx + 6]
                        current_close = df["Close"].iloc[idx]
                        if len(future) < 5 or current_close == 0:
                            continue
                        max_move = float((future.max() - current_close) / current_close)
                        min_move = float((future.min() - current_close) / current_close)
                        label = 1 if (max_move >= MOVE_TARGET_PCT or min_move <= -MOVE_TARGET_PCT) else 0

                        row = {"ticker": ticker, "date": df.index[idx], "label": label}
                        row.update(features)
                        rows.append(row)
                except Exception:
                    continue
        except Exception as e:
            print(f"  [trainer] batch error: {e}")
        time.sleep(0.5)

    df_out = pd.DataFrame(rows)
    print(f"[trainer] Built {len(df_out):,} labeled rows.")
    return df_out


FEATURE_COLS = [
    "bb_width_pct", "bb_squeeze", "atr_ratio", "atr_compression",
    "volume_ratio", "volume_surge", "rsi_value", "rsi_extreme",
    "rsi_bull", "rsi_bear", "ema50_pct",
]


def train(force_refetch: bool = False) -> None:
    os.makedirs(SAVE_DIR, exist_ok=True)

    # Load or build training data
    if os.path.exists(CACHE_PARQUET) and not force_refetch:
        print(f"[trainer] Loading cached training data from {CACHE_PARQUET}")
        data = pd.read_parquet(CACHE_PARQUET)
    else:
        tickers = get_sp500_tickers()
        # Skip futures for training (less history, different dynamics)
        data = _fetch_training_data(tickers, years=TRAIN_YEARS)
        if data.empty:
            print("[trainer] No training data — aborting.")
            return
        data.to_parquet(CACHE_PARQUET, index=False)
        print(f"[trainer] Cached training data to {CACHE_PARQUET}")

    # Prepare features
    data = data.dropna(subset=FEATURE_COLS + ["label"])
    data = data.sort_values("date").reset_index(drop=True)

    X = data[FEATURE_COLS].values
    y = data["label"].values

    # Walk-forward split (no lookahead)
    split_idx = int(len(data) * TRAIN_TEST_SPLIT)
    X_train, X_test = X[:split_idx], X[split_idx:]
    y_train, y_test = y[:split_idx], y[split_idx:]

    print(f"[trainer] Train rows: {len(X_train):,} | Test rows: {len(X_test):,}")
    pos_rate = y_train.mean()
    print(f"[trainer] Positive rate (train): {pos_rate:.2%}")

    scale_pos_weight = (1 - pos_rate) / pos_rate if pos_rate > 0 else 1.0

    # Train XGBoost
    model = XGBClassifier(
        n_estimators=300,
        max_depth=5,
        learning_rate=0.05,
        subsample=0.8,
        colsample_bytree=0.8,
        scale_pos_weight=scale_pos_weight,
        use_label_encoder=False,
        eval_metric="logloss",
        random_state=42,
        n_jobs=-1,
    )
    print("[trainer] Training XGBoost...")
    model.fit(
        X_train, y_train,
        eval_set=[(X_test, y_test)],
        verbose=50,
    )

    # Evaluate
    y_pred = model.predict(X_test)
    y_prob = model.predict_proba(X_test)[:, 1]
    print("\n[trainer] Classification Report (test set):")
    print(classification_report(y_test, y_pred))
    try:
        auc = roc_auc_score(y_test, y_prob)
        print(f"[trainer] AUC-ROC: {auc:.4f}")
    except Exception:
        pass

    # Save model and feature names
    with open(MODEL_PATH, "wb") as f:
        pickle.dump(model, f)
    with open(FEATURE_NAMES_PATH, "w") as f:
        json.dump(FEATURE_COLS, f)
    print(f"\n[trainer] Saved model → {MODEL_PATH}")
    print(f"[trainer] Saved feature names → {FEATURE_NAMES_PATH}")


if __name__ == "__main__":
    import sys
    force = "--refetch" in sys.argv
    train(force_refetch=force)
