"""
ORACLE — Daily Intelligence Agent

Runs every weekday at 10 PM ET. Reviews today's trades and predictions,
learns what worked and what didn't, and writes structured insights to
Supabase that every other agent reads at the start of each scan.

The learning loop:
  1. ORACLE reviews predictions vs actual outcomes
  2. Identifies which signals are working, which are failing
  3. Flags market regime patterns
  4. Saves structured directives to Supabase learnings table
  5. Scanner reads ORACLE's latest directives before each scan
     and adjusts its analysis accordingly

ORACLE teaches the other agents so the system gets smarter every day.
"""
from __future__ import annotations
import json
from datetime import datetime, timedelta
import pandas as pd
import anthropic
from config import ANTHROPIC_API_KEY, MOVE_TARGET_PCT

_client = None


def _get_client():
    global _client
    if _client is None:
        _client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    return _client


def _build_prompt(hits_df: pd.DataFrame, misses_df: pd.DataFrame,
                  recent_trades: list[dict]) -> str:
    def summarize(df: pd.DataFrame, label: str) -> str:
        if df.empty:
            return f"{label}: none this period"
        from collections import Counter
        signals_flat = []
        for s in df.get("signals_triggered", pd.Series(dtype=str)).dropna():
            signals_flat.extend([x.strip() for x in str(s).split(";")])
        top      = Counter(signals_flat).most_common(5)
        avg_score = df["score"].mean() if "score" in df else 0
        avg_move  = df["actual_move_5d"].abs().mean() if "actual_move_5d" in df else 0
        dirs      = df.get("direction", pd.Series(dtype=str)).value_counts().to_dict()
        return (
            f"{label} ({len(df)} trades): "
            f"avg score={avg_score:.1f}, avg move={avg_move:.1f}%, "
            f"directions={dirs}, top signals={[s for s,_ in top]}"
        )

    trade_summary = ""
    if recent_trades:
        wins   = [t for t in recent_trades if t.get("realized_pnl", 0) > 0]
        losses = [t for t in recent_trades if t.get("realized_pnl", 0) < 0]
        trade_summary = (
            f"\nRecent closed trades: {len(recent_trades)} total, "
            f"{len(wins)} wins (+${sum(t.get('realized_pnl',0) for t in wins):.2f}), "
            f"{len(losses)} losses (${sum(t.get('realized_pnl',0) for t in losses):.2f})"
        )

    return f"""You are ORACLE, the intelligence core of an AI trading system.
Your job is to learn from recent performance and issue directives that improve every future scan.

RECENT PERFORMANCE:
{summarize(hits_df, 'HITS (target reached)')}
{summarize(misses_df, 'MISSES (target not reached)')}
{trade_summary}

Respond in this exact JSON format (no markdown, no extra text):
{{
  "summary": "2-sentence plain-English summary of what happened",
  "winning_signals": ["signal1", "signal2"],
  "failing_signals": ["signal1", "signal2"],
  "regime_note": "one sentence about current market conditions",
  "scanner_directive": "one specific instruction for the scanner to follow — be concrete, e.g. 'Increase weight on volume_surge for bullish picks' or 'Avoid bearish plays in Technology sector this week'",
  "confidence_threshold_adjust": 0,
  "avoid_sectors": [],
  "favor_directions": "bullish"
}}"""


def run() -> dict:
    """
    Run ORACLE's daily analysis. Saves structured learnings to Supabase
    so every other agent reads and applies them.
    """
    import db
    if not db.db_available():
        print("[ORACLE] No Supabase — skipping.")
        return {}

    print(f"[ORACLE] Daily intelligence cycle — {datetime.today().strftime('%Y-%m-%d %H:%M')}")

    rows = db.load_predictions(limit=500)
    if not rows:
        print("[ORACLE] No predictions to analyze yet.")
        return {}

    df = pd.DataFrame(rows)
    df["date"] = pd.to_datetime(df["date"])

    cutoff    = pd.Timestamp.today() - timedelta(days=5)
    evaluated = df[df["date"] <= cutoff].dropna(subset=["actual_move_5d"])

    if len(evaluated) < 5:
        print(f"[ORACLE] Only {len(evaluated)} evaluated predictions — need 5+ to analyze.")
        return {}

    hits     = evaluated[evaluated["actual_move_5d"].abs() >= MOVE_TARGET_PCT * 100]
    misses   = evaluated[evaluated["actual_move_5d"].abs() <  MOVE_TARGET_PCT * 100]
    hit_rate = len(hits) / len(evaluated)

    print(f"[ORACLE] {len(evaluated)} evaluated | Hit rate: {hit_rate:.1%} | "
          f"Hits: {len(hits)} | Misses: {len(misses)}")

    try:
        from execution.alpaca import get_closed_trade_pnl, is_configured
        recent_trades = get_closed_trade_pnl(days=7) if is_configured() else []
    except Exception:
        recent_trades = []

    prompt = _build_prompt(hits, misses, recent_trades)
    try:
        response = _get_client().messages.create(
            model      = "claude-sonnet-4-6",
            max_tokens = 600,
            messages   = [{"role": "user", "content": prompt}],
        )
        raw_text = response.content[0].text.strip()
        # Strip markdown code fences if Claude wraps the JSON in ```json ... ```
        if raw_text.startswith("```"):
            lines = raw_text.splitlines()
            raw_text = "\n".join(
                l for l in lines
                if not l.strip().startswith("```")
            ).strip()
        directives = json.loads(raw_text)
        print(f"[ORACLE] Directive → {directives.get('scanner_directive','')}")
    except Exception as e:
        print(f"[ORACLE] Claude error: {e}")
        directives = {}

    def top_signals(df: pd.DataFrame, n: int = 3) -> str:
        from collections import Counter
        sigs = []
        for s in df.get("signals_triggered", pd.Series(dtype=str)).dropna():
            sigs.extend([x.strip() for x in str(s).split(";")])
        return ", ".join(s for s, _ in Counter(sigs).most_common(n))

    record = {
        "week_of":            datetime.today().strftime("%Y-%m-%d"),
        "total_predictions":  len(evaluated),
        "hit_rate":           round(hit_rate, 4),
        "top_hit_signals":    top_signals(hits),
        "top_miss_signals":   top_signals(misses),
        "claude_analysis":    directives.get("summary", ""),
        "weight_adjustments": json.dumps(directives),
    }

    db.save_learning(record)
    print(f"[ORACLE] Learnings saved for {record['week_of']}")

    try:
        from alerts.slack import _post
        _post({"text": (
            f"🔮 *ORACLE — {datetime.today().strftime('%b %d, %Y')}*\n"
            f">{directives.get('summary', '')}\n\n"
            f"*Hit rate:* {hit_rate:.1%}  ·  "
            f"*Winning signals:* {', '.join(directives.get('winning_signals', []))}\n"
            f"*Weak signals:* {', '.join(directives.get('failing_signals', []))}\n\n"
            f"📡 *Tomorrow's directive:* _{directives.get('scanner_directive', '—')}_"
        )})
    except Exception:
        pass

    if hit_rate < 0.50 and len(evaluated) >= 20:
        print("[ORACLE] Hit rate below 50% — triggering model retrain...")
        try:
            from model.trainer import train
            train(force_refetch=False)
        except Exception as e:
            print(f"[ORACLE] Retrain failed: {e}")

    return record


def get_latest_directives() -> dict:
    """
    Called by the scanner at the start of every scan.
    Returns ORACLE's most recent structured directives so the scanner
    can apply them — which signals to trust, which sectors to avoid,
    which direction to favor.
    """
    try:
        import db
        if not db.db_available():
            return {}
        learnings = db.load_learnings()
        if not learnings:
            return {}
        raw = learnings[0].get("weight_adjustments", "{}")
        return json.loads(raw) if raw else {}
    except Exception:
        return {}


if __name__ == "__main__":
    run()
