"""
Market Predictions Agent — full 5-agent pipeline.

  1. Scan Agent    — fetch universe OHLCV + filter
  2. Research Agent — parallel Reddit + RSS + news sentiment
  3. Prediction Agent — XGBoost + sentiment → scored picks
  4. Risk Agent    — Kelly Criterion position sizing
  5. Learning Agent — backfill actuals, weekly post-mortem

Optional: Alpaca execution for High-confidence picks (paper mode by default).

Run:
    python agent.py              # full scan + email + Alpaca (if configured)
    python agent.py --no-email   # skip email
    python agent.py --no-trade   # skip Alpaca execution
    python agent.py --postmortem # run learning agent only
"""
import sys
import time
import pandas as pd
from datetime import datetime

from data.universe import get_universe
from data.fetcher import get_ohlcv_batch, get_earnings_days
from data.research import research_universe
from signals.sentiment import get_sentiment_with_velocity
from signals.kelly import annotate_picks
from signals.market_regime import get_market_regime
from signals.options_flow import enrich_with_options
from model.predictor import predict_universe, model_available
from analyst.claude_analyst import explain_picks
from alerts.slack import send_trade_alert
from risk.portfolio_guard import check_trade, increment_daily_count
from config import (TOP_N_CLAUDE_ANALYSIS, MIN_SCORE_TO_ALERT,
                    AUTO_EXECUTE_MIN_SCORE, BANKROLL, ENABLE_OPTIONS_FLOW)
import db


def _backfill_actual_moves(ohlcv_map: dict) -> None:
    if not db.db_available():
        return
    rows = db.load_predictions()
    if not rows:
        return
    log = pd.DataFrame(rows)
    today = pd.Timestamp.today().normalize()
    changed = 0
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
            entry = float(df.loc[df.index <= pred_date]["Close"].iloc[-1])
            max_move = (float(future.max()) - entry) / entry * 100
            min_move = (float(future.min()) - entry) / entry * 100
            actual = max_move if abs(max_move) >= abs(min_move) else min_move
            db.update_actual_move(str(row["date"]), ticker, actual)
            changed += 1
        except Exception:
            continue
    if changed:
        print(f"[agent] Backfilled {changed} actual moves.")


def _execute_trades(picks_df: pd.DataFrame, explanations: dict,
                    regime: dict | None = None) -> list[dict]:
    """Auto-execute High-confidence picks via Alpaca (paper by default)."""
    from execution.alpaca import is_configured, place_order, is_live_mode, get_positions, get_account
    if not is_configured():
        print("[agent] Alpaca not configured — skipping execution.")
        return []

    mode = "LIVE 🔴" if is_live_mode() else "PAPER 📄"
    print(f"\n[agent] Alpaca execution ({mode})")

    # Regime gate: if market is in bear regime, skip bullish auto-exec
    if regime and not regime.get("auto_exec_ok", True):
        print(f"[agent] ⚠ Regime gate: {regime.get('warning')} — skipping bullish auto-exec")

    # Fetch current positions + account for portfolio guard
    try:
        open_positions  = get_positions()
        account         = get_account()
        portfolio_value = account.get("portfolio_value", BANKROLL)
    except Exception:
        open_positions  = []
        portfolio_value = BANKROLL

    results    = []
    auto_picks = picks_df[picks_df["score"] >= AUTO_EXECUTE_MIN_SCORE]
    for _, row in auto_picks.iterrows():
        ticker    = row["ticker"]
        direction = row.get("direction", "bullish")
        dollar    = row.get("dollar_amount", 0)
        if dollar <= 0:
            continue

        # Regime multiplier — reduce position size when market is risky
        if regime and direction == "bullish":
            multiplier = regime.get("bull_multiplier", 1.0)
            if multiplier < 1.0:
                dollar = round(dollar * multiplier, 2)
                print(f"  {ticker}: position reduced to ${dollar:.0f} (regime multiplier {multiplier:.0%})")

            # Hard block on bullish trades in bear regime
            if not regime.get("auto_exec_ok", True):
                print(f"  {ticker}: SKIPPED — bear regime active")
                continue

        # Portfolio guard check
        ok, guard_reason = check_trade(ticker, dollar, direction, open_positions, portfolio_value)
        if not ok:
            print(f"  {ticker}: BLOCKED by portfolio guard — {guard_reason}")
            continue
        if guard_reason != "ok":
            print(f"  {ticker}: {guard_reason}")

        reason = explanations.get(ticker, "")[:120]
        result = place_order(ticker, dollar, direction, reason)
        results.append(result)
        print(f"  {ticker}: {result.get('status')} ${dollar:.0f} {direction}")
        send_trade_alert(result)   # instant Slack ping when bracket order placed
        if result.get("status") == "submitted":
            increment_daily_count()

    return results


def run_scan(send_email: bool = True,
             execute_trades: bool = True,
             verbose: bool = True) -> pd.DataFrame:
    start = time.time()
    today = datetime.today().strftime("%Y-%m-%d")

    print(f"\n{'='*62}")
    print(f"  Market Predictions Agent  |  {today}")
    print(f"  Model:   {'XGBoost ✓' if model_available() else 'Rule-based (no model)'}")
    print(f"  DB:      {'Supabase ✓' if db.db_available() else 'local only'}")
    print(f"  Bankroll: ${BANKROLL:,.0f}")
    print(f"{'='*62}\n")

    # ── 0. Market Regime ─────────────────────────────────────────
    print(f"[0/5] REGIME — VIX + SPY trend + sector breadth")
    _neutral_regime = {"regime":"neutral","vix":20.0,"vix_level":"normal",
                       "spy_vs_200ma_pct":0.0,"spy_vs_50ma_pct":0.0,"spy_trend":"sideways",
                       "sectors_above_50ma":5,"breadth":"normal","bull_multiplier":1.0,
                       "auto_exec_ok":True,"warning":None}
    try:
        regime = get_market_regime()
        regime_icon = {"bull": "🟢", "neutral": "🟡", "bear": "🔴"}.get(regime["regime"], "⚪")
        print(f"      {regime_icon} {regime['regime'].upper()} · VIX {regime['vix']} · "
              f"SPY {regime['spy_vs_200ma_pct']:+.1f}% vs 200MA · "
              f"{regime['sectors_above_50ma']}/11 sectors above 50MA")
        if regime.get("warning"):
            print(f"      ⚠ {regime['warning']}")
    except Exception as e:
        print(f"      ⚠ Regime check failed ({e}) — proceeding as neutral")
        regime = _neutral_regime

    # ── 1. Scan ───────────────────────────────────────────────────
    tickers = get_universe()
    print(f"\n[1/5] SCAN — {len(tickers)} tickers")
    ohlcv_map = get_ohlcv_batch(tickers, period="1y", chunk_size=50)
    print(f"      Got data for {len(ohlcv_map)} tickers")
    _backfill_actual_moves(ohlcv_map)

    # ── 2. Research (parallel) ────────────────────────────────────
    print(f"\n[2/5] RESEARCH — parallel Reddit + RSS + news")
    blended_sentiment = research_universe(tickers)

    # Persist sentiment velocity via existing cache
    sentiment_map: dict = {}
    for ticker in tickers:
        cached = get_sentiment_with_velocity(ticker)
        blended = blended_sentiment.get(ticker, {})
        # Blend cached velocity with new multi-source score
        combined_score = (cached.get("score", 0.0) * 0.4 +
                          blended.get("score", 0.0) * 0.6)
        sentiment_map[ticker] = {
            **blended,
            "score": round(combined_score, 4),
            "velocity": cached.get("velocity", 0.0),
            "spike": abs(cached.get("velocity", 0.0)) >= 0.3 or blended.get("score", 0) > 0.4,
        }

    # ── 3. Predict ────────────────────────────────────────────────
    print(f"\n[3/5] PREDICT — XGBoost + blended sentiment")
    earnings_map: dict = {}
    for ticker in tickers[:100]:
        earnings_map[ticker] = get_earnings_days(ticker)

    picks_df = predict_universe(tickers, ohlcv_map, sentiment_map, earnings_map)

    if picks_df is None or picks_df.empty:
        print("[agent] No setups above threshold today.")
        return pd.DataFrame()

    print(f"      {len(picks_df)} setups flagged (score ≥ {MIN_SCORE_TO_ALERT})")

    # ── 3.5. Enrich top picks with options flow ───────────────────
    if ENABLE_OPTIONS_FLOW and not picks_df.empty:
        top_picks = picks_df[picks_df["score"] >= 60].head(15)
        if not top_picks.empty:
            try:
                print(f"\n[3.5] ENRICH — options flow ({len(top_picks)} tickers)")
                enriched = enrich_with_options(top_picks, verbose=True)
                for idx in enriched.index:
                    t    = enriched.loc[idx, "ticker"]
                    mask = picks_df["ticker"] == t
                    picks_df.loc[mask, "score"] = enriched.loc[idx, "score"]
                    for col in ["options_side","options_pcr","options_unusual","options_detail"]:
                        if col in enriched.columns:
                            picks_df.loc[mask, col] = enriched.loc[idx, col]
                picks_df = picks_df.sort_values("score", ascending=False).reset_index(drop=True)
            except Exception as e:
                print(f"      ⚠ Options enrichment failed ({e}) — continuing without it")

    # ── 4. Risk — Kelly Criterion ─────────────────────────────────
    print(f"\n[4/5] RISK — Kelly Criterion sizing (bankroll ${BANKROLL:,.0f})")
    picks_df = annotate_picks(picks_df)
    for _, row in picks_df.head(10).iterrows():
        print(f"      {row['ticker']:6s}  score={row['score']:.0f}  "
              f"${row.get('dollar_amount',0):,.0f}  ({row.get('risk_level','')})")

    # Claude explanations
    print(f"\n      Generating Claude analysis for top {TOP_N_CLAUDE_ANALYSIS}...")
    explanations = explain_picks(picks_df, top_n=TOP_N_CLAUDE_ANALYSIS)

    # ── 5. Learn — persist + optionally execute ───────────────────
    print(f"\n[5/5] LEARN — persist predictions")
    if db.db_available():
        rows = picks_df.copy()
        rows["date"] = today
        rows["actual_move_5d"] = None
        db.append_predictions(rows.to_dict(orient="records"))
        print(f"      Saved {len(rows)} predictions to Supabase")

    # Alpaca execution
    if execute_trades:
        trade_results = _execute_trades(picks_df, explanations, regime=regime)
    else:
        print("      Alpaca execution skipped (--no-trade)")
        trade_results = []


    elapsed = time.time() - start
    print(f"\n{'='*62}")
    print(f"  Done in {elapsed:.1f}s | {len(picks_df)} setups | "
          f"{len(trade_results)} trades placed")
    print(f"{'='*62}\n")
    return picks_df


if __name__ == "__main__":
    args = sys.argv[1:]

    if "--postmortem" in args:
        from analyst.learning_agent import run_postmortem
        run_postmortem()
    else:
        run_scan(
            send_email="--no-email" not in args,
            execute_trades="--no-trade" not in args,
        )
