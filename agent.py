"""
Main agent pipeline. Run directly:
    python agent.py              # scan + email
    python agent.py --no-email  # scan without email

Steps:
  1. Fetch OHLCV for full universe
  2. Fetch news sentiment per ticker
  3. Fetch earnings proximity
  4. Score / predict using XGBoost (or rule-based fallback)
  5. Explain top picks via Claude
  6. Persist to Supabase (predictions + backfill actual moves)
  7. Send email digest
"""
import sys
import time
import pandas as pd
from datetime import datetime

from data.universe import get_universe
from data.fetcher import get_ohlcv_batch, get_earnings_days
from signals.sentiment import get_sentiment_with_velocity
from model.predictor import predict_universe, model_available
from analyst.claude_analyst import explain_picks
from alerts.email import send_daily_digest
from config import TOP_N_CLAUDE_ANALYSIS, MIN_SCORE_TO_ALERT
import db


def _backfill_actual_moves(ohlcv_map: dict) -> None:
    """Fill in actual_move_5d for predictions older than 5 trading days."""
    if not db.db_available():
        return
    rows = db.load_predictions()
    if not rows:
        return

    log = pd.DataFrame(rows)
    today = pd.Timestamp.today().normalize()

    for _, row in log.iterrows():
        if pd.notna(row.get("actual_move_5d")):
            continue
        pred_date = pd.to_datetime(row["date"])
        if (today - pred_date).days < 7:
            continue

        ticker = row["ticker"]
        df = ohlcv_map.get(ticker)
        if df is None or df.empty:
            continue

        try:
            df.index = pd.to_datetime(df.index)
            future = df.loc[df.index > pred_date]["Close"].head(5)
            if len(future) < 3:
                continue
            entry = df.loc[df.index <= pred_date]["Close"].iloc[-1]
            max_move = (future.max() - entry) / entry * 100
            min_move = (future.min() - entry) / entry * 100
            actual = max_move if abs(max_move) >= abs(min_move) else min_move
            db.update_actual_move(str(row["date"]), ticker, actual)
        except Exception:
            continue

    print("[agent] Backfill of actual moves complete.")


def run_scan(send_email: bool = True, verbose: bool = True) -> pd.DataFrame:
    start = time.time()
    today = datetime.today().strftime("%Y-%m-%d")
    print(f"\n{'='*60}")
    print(f"  Market Predictions Agent — {today}")
    print(f"  Model: {'XGBoost' if model_available() else 'Rule-based fallback'}")
    print(f"  DB:    {'Supabase' if db.db_available() else 'local only (no Supabase creds)'}")
    print(f"{'='*60}\n")

    # 1. Universe
    tickers = get_universe()
    print(f"[agent] Universe: {len(tickers)} tickers")

    # 2. Fetch OHLCV (1 year of history)
    print("[agent] Fetching OHLCV data...")
    ohlcv_map = get_ohlcv_batch(tickers, period="1y", chunk_size=50)
    print(f"[agent] Got data for {len(ohlcv_map)} tickers")

    # 3. Backfill old predictions
    _backfill_actual_moves(ohlcv_map)

    # 4. Sentiment (with Supabase cache)
    print("[agent] Fetching sentiment scores...")
    sentiment_map: dict = {}
    for i, ticker in enumerate(tickers):
        sentiment_map[ticker] = get_sentiment_with_velocity(ticker)
        if (i + 1) % 50 == 0:
            print(f"  {i+1}/{len(tickers)} sentiment scores done")

    # 5. Earnings proximity (sampled to avoid rate limits)
    print("[agent] Fetching earnings dates (sampled)...")
    earnings_map: dict = {}
    for ticker in tickers[:100]:
        earnings_map[ticker] = get_earnings_days(ticker)

    # 6. Score / predict
    print("[agent] Scoring universe...")
    picks_df = predict_universe(tickers, ohlcv_map, sentiment_map, earnings_map)

    if picks_df is None or picks_df.empty:
        print("[agent] No setups above threshold today.")
        return pd.DataFrame()

    print(f"\n[agent] {len(picks_df)} setups flagged (score ≥ {MIN_SCORE_TO_ALERT}):\n")
    display_cols = ["ticker", "score", "direction", "duration", "confidence"]
    available = [c for c in display_cols if c in picks_df.columns]
    print(picks_df[available].to_string(index=False))

    # 7. Claude explanations for top picks
    print(f"\n[agent] Generating Claude analysis for top {TOP_N_CLAUDE_ANALYSIS}...")
    explanations = explain_picks(picks_df, top_n=TOP_N_CLAUDE_ANALYSIS)
    for ticker, text in explanations.items():
        print(f"\n--- {ticker} ---\n{text}")

    # 8. Persist to Supabase
    if db.db_available():
        rows = picks_df.copy()
        rows["date"] = today
        rows["actual_move_5d"] = None
        db.append_predictions(rows.to_dict(orient="records"))
        print(f"\n[agent] Saved {len(rows)} predictions to Supabase.")
    else:
        print("\n[agent] No Supabase credentials — predictions not persisted.")

    # 9. Email digest
    if send_email:
        send_daily_digest(picks_df.head(TOP_N_CLAUDE_ANALYSIS), explanations)

    elapsed = time.time() - start
    print(f"\n[agent] Done in {elapsed:.1f}s")
    return picks_df


if __name__ == "__main__":
    no_email = "--no-email" in sys.argv
    run_scan(send_email=not no_email)
