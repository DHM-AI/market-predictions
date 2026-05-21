"""
Sentiment Guard — runs every hour during market hours via GitHub Actions.

For each open position it:
  1. Fetches fresh sentiment score for that ticker
  2. Checks if sentiment has reversed against the trade direction
  3. Takes tiered protective action:

     LONG positions:
       score < -0.15  →  WARNING  — Slack alert, no action yet
       score < -0.35  →  DANGER   — tighten stop to 1.5% below current price
       score < -0.60  →  CRITICAL — close position immediately

     SHORT positions: same logic inverted (positive sentiment = danger)

Config thresholds in config.py:
  GUARD_WARN_THRESHOLD    = -0.15
  GUARD_TIGHTEN_THRESHOLD = -0.35
  GUARD_CLOSE_THRESHOLD   = -0.60
"""
import sys
from datetime import datetime

from config import (GUARD_WARN_THRESHOLD, GUARD_TIGHTEN_THRESHOLD,
                    GUARD_CLOSE_THRESHOLD)
from execution.alpaca import get_positions, tighten_stop, close_position, is_configured
from signals.sentiment import get_sentiment_with_velocity


def _slack(text: str) -> None:
    try:
        from alerts.slack import _post
        _post({"text": text})
    except Exception:
        pass


def run_guard() -> list[dict]:
    if not is_configured():
        print("[guard] Alpaca not configured — skipping.")
        return []

    positions = get_positions()
    if not positions:
        print("[guard] No open positions.")
        return []

    print(f"[guard] Checking sentiment for {len(positions)} position(s)...")
    actions = []

    for p in positions:
        ticker   = p["ticker"]
        raw_side = str(p.get("side", "")).lower()
        is_long  = "long" in raw_side or "buy" in raw_side
        pl_pct   = p.get("unrealized_pl_pct", 0)

        try:
            sent = get_sentiment_with_velocity(ticker)
        except Exception as e:
            print(f"[guard] Sentiment fetch failed for {ticker}: {e}")
            continue

        score    = sent.get("score", 0.0)
        velocity = sent.get("velocity", 0.0)

        # For longs: negative score is bad. For shorts: positive score is bad.
        danger_score = score if is_long else -score

        direction_lbl = "LONG" if is_long else "SHORT"
        print(f"  {ticker:6s} {direction_lbl}  sentiment={score:+.3f}  "
              f"velocity={velocity:+.3f}  P&L={pl_pct:+.1f}%")

        # ── CRITICAL — close immediately ──────────────────────────────────────
        if danger_score < GUARD_CLOSE_THRESHOLD:
            print(f"  ⛔ {ticker} CRITICAL sentiment reversal — closing position")
            result = close_position(ticker)
            _slack(
                f"⛔ *Sentiment Guard — CLOSING {ticker}* ({direction_lbl})\n"
                f">Sentiment: *{score:+.3f}* (strongly {'bearish' if is_long else 'bullish'})\n"
                f">Position P&L at close: *{pl_pct:+.1f}%*\n"
                f">Action: *Position closed* to protect capital"
            )
            actions.append({
                "ticker": ticker, "action": "closed",
                "score": score, "pl_pct": pl_pct,
            })

        # ── DANGER — tighten stop ─────────────────────────────────────────────
        elif danger_score < GUARD_TIGHTEN_THRESHOLD:
            print(f"  ⚠️  {ticker} DANGER — tightening stop to 1.5%")
            result = tighten_stop(ticker, stop_pct=0.015)
            new_stop = result.get("new_stop", "—")
            _slack(
                f"⚠️ *Sentiment Guard — Stop Tightened: {ticker}* ({direction_lbl})\n"
                f">Sentiment: *{score:+.3f}* ({'bearish' if is_long else 'bullish'} shift)\n"
                f">Stop loss tightened to *${new_stop}* (1.5% below current price)\n"
                f">Position P&L: *{pl_pct:+.1f}%* · Take-profit target unchanged"
            )
            actions.append({
                "ticker": ticker, "action": "tightened",
                "score": score, "new_stop": new_stop, "pl_pct": pl_pct,
            })

        # ── WARNING — alert only ──────────────────────────────────────────────
        elif danger_score < GUARD_WARN_THRESHOLD:
            print(f"  🟡 {ticker} WARNING — sentiment weakening, watching")
            _slack(
                f"🟡 *Sentiment Guard — Warning: {ticker}* ({direction_lbl})\n"
                f">Sentiment: *{score:+.3f}* (weakening, velocity {velocity:+.3f})\n"
                f">Position P&L: *{pl_pct:+.1f}%* · No action yet — monitoring\n"
                f">If sentiment drops further, stop will be tightened automatically"
            )
            actions.append({
                "ticker": ticker, "action": "warned",
                "score": score, "pl_pct": pl_pct,
            })

        else:
            print(f"  ✅ {ticker} sentiment OK ({score:+.3f})")

    return actions


if __name__ == "__main__":
    print(f"Sentiment Guard — {datetime.now().strftime('%Y-%m-%d %H:%M ET')}")
    print("=" * 50)
    results = run_guard()
    print("=" * 50)
    if results:
        print(f"\n{len(results)} action(s) taken:")
        for r in results:
            print(f"  {r['ticker']:6s}  {r['action'].upper():10s}  "
                  f"score={r['score']:+.3f}  P&L={r['pl_pct']:+.1f}%")
    else:
        print("All positions sentiment OK — no action needed.")
