from __future__ import annotations
"""
Calibration drift check.

After Platt scaling, a "0.70 calibrated probability" should mean "70% of
those picks actually win." Over time the model can drift (regime shift,
feature distribution change) and predicted vs actual rates diverge.

This module pulls the last 60 days of predictions from Supabase, buckets
them by calibrated probability decile, and compares predicted-rate to
actual-rate. If any bucket is off by more than DRIFT_THRESHOLD_PCT, sends
a Slack alert + writes the report to `model_drift_log`.

Scheduled weekly via .github/workflows/drift_check.yml (Sunday 9 AM ET).

Schema (created lazily — also in the migration file):
    CREATE TABLE IF NOT EXISTS model_drift_log (
      id          BIGSERIAL PRIMARY KEY,
      checked_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
      total_rows  INT,
      max_drift   NUMERIC,
      flagged     BOOLEAN,
      report      JSONB
    );

Usage:
    python -m model.drift_check
"""
from datetime import datetime, timedelta, timezone

from db import _client
from alerts.slack import _post


DRIFT_THRESHOLD_PCT = 12.0   # bucket flagged if predicted vs actual differs by more than this
LOOKBACK_DAYS       = 60
MIN_BUCKET_SIZE     = 10     # need at least N predictions in a bucket to evaluate


BUCKETS = [
    (0.30, 0.40),
    (0.40, 0.50),
    (0.50, 0.60),
    (0.60, 0.70),
    (0.70, 0.80),
    (0.80, 1.01),
]


def _load_recent_predictions(days: int = LOOKBACK_DAYS) -> list[dict]:
    """Pull predictions with both xgb_prob and an actual_move_5d outcome."""
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).date().isoformat()
    try:
        res = (_client().table("predictions")
                .select("date,ticker,xgb_prob,actual_move_5d,direction,score")
                .gte("date", cutoff)
                .not_.is_("actual_move_5d", None)
                .not_.is_("xgb_prob", None)
                .execute())
        return res.data or []
    except Exception as e:
        print(f"[drift] Failed to load predictions: {e}")
        return []


def _classify_win(row: dict) -> bool | None:
    """
    Did the prediction win? A "win" for bullish = +5%+ move within 5 days;
    bearish = -5%+ move. Returns None if direction or move missing.
    """
    move = row.get("actual_move_5d")
    direction = (row.get("direction") or "").lower()
    if move is None:
        return None
    try:
        move = float(move)
    except Exception:
        return None
    if direction == "bullish":
        return move >= 0.05
    if direction == "bearish":
        return move <= -0.05
    return None


def evaluate_drift() -> dict:
    """
    Run the drift evaluation. Returns:
      {
        "total_rows":     int,
        "buckets":        [{lo, hi, n, pred_avg, actual_rate, drift}, ...],
        "max_drift":      float,
        "flagged":        bool,
        "flagged_buckets": [{lo, hi, drift}, ...],
      }
    """
    rows = _load_recent_predictions()
    if not rows:
        return {"total_rows": 0, "buckets": [], "max_drift": 0.0, "flagged": False, "flagged_buckets": []}

    enriched = []
    for r in rows:
        win = _classify_win(r)
        if win is None:
            continue
        try:
            prob = float(r.get("xgb_prob"))
        except Exception:
            continue
        enriched.append({"prob": prob, "win": 1 if win else 0})

    buckets_out = []
    flagged = []
    max_drift = 0.0
    for lo, hi in BUCKETS:
        in_bucket = [e for e in enriched if lo <= e["prob"] < hi]
        n = len(in_bucket)
        if n < MIN_BUCKET_SIZE:
            buckets_out.append({"lo": lo, "hi": hi, "n": n, "pred_avg": None,
                                "actual_rate": None, "drift": None})
            continue
        pred_avg = sum(e["prob"] for e in in_bucket) / n
        actual_rate = sum(e["win"] for e in in_bucket) / n
        drift_pct = (actual_rate - pred_avg) * 100
        buckets_out.append({
            "lo": lo, "hi": hi, "n": n,
            "pred_avg": round(pred_avg, 3),
            "actual_rate": round(actual_rate, 3),
            "drift": round(drift_pct, 1),
        })
        if abs(drift_pct) > DRIFT_THRESHOLD_PCT:
            flagged.append({"lo": lo, "hi": hi, "drift": round(drift_pct, 1)})
        max_drift = max(max_drift, abs(drift_pct))

    return {
        "total_rows": len(enriched),
        "buckets": buckets_out,
        "max_drift": round(max_drift, 1),
        "flagged": bool(flagged),
        "flagged_buckets": flagged,
    }


def _save_to_supabase(report: dict) -> None:
    """Persist the drift report so we have history."""
    try:
        _client().table("model_drift_log").insert({
            "total_rows": report["total_rows"],
            "max_drift":  report["max_drift"],
            "flagged":    report["flagged"],
            "report":     report,
        }).execute()
    except Exception as e:
        print(f"[drift] Failed to save drift log: {e}")


def _slack_report(report: dict) -> None:
    """Send Slack message about the drift check result."""
    if not report["total_rows"]:
        _post({"text": "🩺 *Calibration drift check* — no recent predictions to evaluate."})
        return

    color = "danger" if report["flagged"] else "good"
    header = "⚠️ Model drift detected" if report["flagged"] else "✅ Model calibration on track"

    bucket_lines = []
    for b in report["buckets"]:
        if b["pred_avg"] is None:
            bucket_lines.append(f"  {b['lo']:.2f}-{b['hi']:.2f}   n={b['n']:>3}   (skipped — too few)")
        else:
            arrow = "🔴" if abs(b["drift"]) > DRIFT_THRESHOLD_PCT else "🟢"
            bucket_lines.append(
                f"  {b['lo']:.2f}-{b['hi']:.2f}   n={b['n']:>3}   "
                f"pred={b['pred_avg']:.2f}   actual={b['actual_rate']:.2f}   "
                f"drift={b['drift']:+.1f}%  {arrow}"
            )
    text = (
        f"*{header}*\n"
        f"_{report['total_rows']} predictions over last {LOOKBACK_DAYS}d · "
        f"max drift = {report['max_drift']:.1f}%_\n"
        f"```\n" + "\n".join(bucket_lines) + "\n```"
    )
    if report["flagged"]:
        text += (
            "\n*Action:* consider re-running `python -m model.trainer --refetch` to refit "
            "the Platt scaling on fresh data."
        )

    _post({
        "attachments": [{
            "color": color,
            "text":  text,
            "mrkdwn_in": ["text"],
            "footer": "Illuminati · Drift Check",
            "ts": int(datetime.now().timestamp()),
        }]
    })


def main() -> int:
    print("[drift] Running calibration drift check...")
    report = evaluate_drift()
    print(f"[drift] {report['total_rows']} predictions evaluated. "
          f"Max drift = {report['max_drift']}%. Flagged = {report['flagged']}.")
    _save_to_supabase(report)
    _slack_report(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
