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


def _get_cached_sentiment(ticker: str) -> dict:
    """
    Read sentiment from Supabase cache only — no live API calls.
    The main scan already fetches and caches sentiment 12×/day.
    Avoids burning Alpha Vantage's 25 req/day limit in the hourly guard.
    """
    try:
        import db
        if db.db_available():
            cache = db.load_sentiment_cache()
            ticker_history = cache.get(ticker, {})
            if ticker_history:
                latest_date  = max(ticker_history.keys())
                latest_score = ticker_history[latest_date]
                dates = sorted(ticker_history.keys(), reverse=True)
                prior_score  = ticker_history[dates[1]] if len(dates) > 1 else None
                velocity     = (latest_score - prior_score) if prior_score is not None else 0.0
                return {"score": latest_score, "velocity": velocity,
                        "spike": abs(velocity) >= 0.3, "source": "cache"}
    except Exception:
        pass
    return {"score": 0.0, "velocity": 0.0, "spike": False, "source": "unavailable"}


def _slack(text: str, dedup_key: str | None = None,
           cooldown_hours: int = 6) -> None:
    """Post to Slack with optional per-key dedup window.

    N-6 fix: VIGIL was Slacking every ticker every cycle — 70+ messages/day
    if multiple positions trended negative. With dedup_key set, same key
    only posts once per cooldown_hours.
    """
    if dedup_key:
        try:
            import db as _db
            if _db.db_available():
                from datetime import datetime as _dt, timedelta as _td
                # Look up most recent alert for this key
                cutoff = (_dt.utcnow() - _td(hours=cooldown_hours)).isoformat()
                _rows = (_db._client().table("trades")
                            .select("timestamp")
                            .eq("status", f"vigil_alert:{dedup_key}")
                            .gte("timestamp", cutoff)
                            .limit(1).execute())
                if _rows.data:
                    return   # silenced by cooldown
                # Record this alert so next call in cooldown silences
                _db.save_trade({
                    "order_id":  f"vigil-{dedup_key}-{int(_dt.utcnow().timestamp())}",
                    "ticker":    dedup_key.split(":")[0] if ":" in dedup_key else dedup_key,
                    "side":      "alert",
                    "dollar_amount": 0,
                    "mode":      "PAPER",
                    "status":    f"vigil_alert:{dedup_key}",
                    "reason":    text[:200],
                    "timestamp": _dt.utcnow().isoformat(),
                })
        except Exception:
            pass   # if dedup fails, fall through and just post
    try:
        from alerts.slack import _post
        _post({"text": text})
    except Exception:
        pass


def run_guard() -> list[dict]:
    if not is_configured():
        print("[VIGIL] Alpaca not configured — skipping.")
        return []

    positions = get_positions()
    if not positions:
        print("[VIGIL] No open positions.")
        return []

    print(f"[VIGIL] Checking sentiment for {len(positions)} position(s)...")
    actions = []

    for p in positions:
        ticker   = p["ticker"]
        raw_side = str(p.get("side", "")).lower()
        is_long  = "long" in raw_side or "buy" in raw_side
        pl_pct   = p.get("unrealized_pl_pct", 0)

        sent = _get_cached_sentiment(ticker)
        if sent["source"] == "unavailable":
            print(f"  {ticker:6s} — no cached sentiment, skipping")
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
                f">Position P&L: *{pl_pct:+.1f}%* · Take-profit target unchanged",
                dedup_key=f"{ticker}:tighten", cooldown_hours=6,
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
                f">If sentiment drops further, stop will be tightened automatically",
                dedup_key=f"{ticker}:warn", cooldown_hours=12,
            )
            actions.append({
                "ticker": ticker, "action": "warned",
                "score": score, "pl_pct": pl_pct,
            })

        else:
            print(f"  ✅ {ticker} sentiment OK ({score:+.3f})")

    return actions


if __name__ == "__main__":
    print(f"[VIGIL] Sentiment Guard — {datetime.now().strftime('%Y-%m-%d %H:%M ET')}")
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
