import anthropic
from config import ANTHROPIC_API_KEY, TOP_N_CLAUDE_ANALYSIS

client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)


def _build_prompt(row: dict) -> str:
    signals = ", ".join(row.get("signals_triggered", [])) or "None triggered"
    return (
        f"You are a quantitative analyst. A market scanner flagged {row['ticker']} with the following data:\n\n"
        f"- Direction: {row.get('direction', 'unknown')}\n"
        f"- Expected move window: {row.get('duration', 'unknown')}\n"
        f"- Composite score: {row.get('score', 0)}/100\n"
        f"- Signals triggered: {signals}\n"
        f"- RSI: {row.get('rsi', 'N/A')}\n"
        f"- BB width percentile: {row.get('bb_pct', 'N/A')} (lower = tighter squeeze)\n"
        f"- ATR ratio (current/50d avg): {row.get('atr_ratio', 'N/A')}\n"
        f"- Volume ratio (today/20d avg): {row.get('volume_ratio', 'N/A')}x\n"
        f"- EMA50 offset: {row.get('ema50_pct', 'N/A')}%\n"
        f"- Sentiment score: {row.get('sentiment_score', 0):.3f} | Velocity (Δ7d): {row.get('sentiment_velocity', 0):.3f}\n"
        f"- Days to earnings: {row.get('earnings_days', 'N/A')}\n\n"
        f"In exactly 3 concise bullet points, explain why {row['ticker']} may move 5%+ within the predicted window. "
        f"Be specific about the technical setup. No filler, no hedging phrases like 'it is important to note'."
    )


def explain_picks(scored_df, top_n: int = TOP_N_CLAUDE_ANALYSIS) -> dict[str, str]:
    """
    Returns {ticker: markdown_explanation} for the top N picks.
    Uses non-streaming for batch processing (email/logging).
    """
    if scored_df is None or scored_df.empty:
        return {}

    results: dict[str, str] = {}
    top = scored_df.head(top_n)

    for _, row in top.iterrows():
        ticker = row["ticker"]
        prompt = _build_prompt(row.to_dict())
        try:
            message = client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=400,
                messages=[{"role": "user", "content": prompt}],
            )
            results[ticker] = message.content[0].text
        except Exception as e:
            results[ticker] = f"Analysis unavailable: {e}"

    return results


def stream_explanation(row: dict):
    """
    Generator that yields text chunks for a single ticker.
    Used by the Streamlit deep-dive page for live streaming.
    """
    prompt = _build_prompt(row)
    try:
        with client.messages.stream(
            model="claude-sonnet-4-6",
            max_tokens=400,
            messages=[{"role": "user", "content": prompt}],
        ) as stream:
            for text in stream.text_stream:
                yield text
    except Exception as e:
        yield f"\n\n_Analysis error: {e}_"
