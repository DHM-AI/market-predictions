import streamlit as st
import plotly.graph_objects as go
import plotly.subplots as sp
import pandas_ta as ta

st.set_page_config(page_title="Ticker Deep Dive", page_icon="📊", layout="wide")
st.title("Ticker Deep Dive")
st.caption("Analyze any ticker on demand — full signal breakdown + Claude explanation.")

ticker_input = st.text_input("Enter ticker symbol", placeholder="AAPL, TSLA, ES=F, NQ=F ...")
analyze_clicked = st.button("Analyze", type="primary")

if not ticker_input or not analyze_clicked:
    st.stop()

ticker = ticker_input.upper().strip()

with st.spinner(f"Fetching data for {ticker}..."):
    from data.fetcher import get_ohlcv, get_earnings_days
    from signals.technicals import compute_all
    from signals.sentiment import get_sentiment_with_velocity
    from signals.scorer import score_ticker

    df = get_ohlcv(ticker, period="1y")
    if df.empty:
        st.error(f"No price data found for {ticker}. Check the symbol and try again.")
        st.stop()

    sentiment = get_sentiment_with_velocity(ticker)
    earnings_days = get_earnings_days(ticker)
    technicals = compute_all(df)
    result = score_ticker(ticker, df, sentiment, earnings_days)

# ── Score header ──────────────────────────────────────────────────────────────
col_score, col_dir, col_dur, col_conf = st.columns(4)
col_score.metric("Score", f"{result['score']}/100")
col_dir.metric("Direction", result["direction"].capitalize())
col_dur.metric("Expected Window", result["duration"])
col_conf.metric("Confidence", result["confidence"])

signals = result.get("signals_triggered", [])
if signals:
    st.markdown("**Signals triggered:** " + " · ".join(f"`{s}`" for s in signals))
else:
    st.info("No strong signals triggered at current thresholds.")

st.divider()

# ── Signal detail table ───────────────────────────────────────────────────────
st.subheader("Signal Breakdown")
sig_data = {
    "Signal": ["BB Squeeze", "ATR Compression", "Volume Surge", "RSI Extreme", "Sentiment Spike"],
    "Value": [
        f"Width pct={technicals['bb']['width_percentile']}",
        f"Ratio={technicals['atr']['ratio']}",
        f"Ratio={technicals['vol']['ratio']}x",
        f"RSI={technicals['rsi']['value']} ({technicals['rsi']['side']})",
        f"Score={sentiment['score']:.3f} Δ={sentiment['velocity']:.3f}",
    ],
    "Triggered": [
        "✅" if technicals["bb"]["triggered"] else "—",
        "✅" if technicals["atr"]["triggered"] else "—",
        "✅" if technicals["vol"]["triggered"] else "—",
        "✅" if technicals["rsi"]["extreme"] else "—",
        "✅" if sentiment["spike"] else "—",
    ],
    "Points": [
        result["breakdown"].get("bb_squeeze", 0),
        result["breakdown"].get("atr_compression", 0),
        result["breakdown"].get("volume_surge", 0),
        result["breakdown"].get("rsi_extreme", 0),
        result["breakdown"].get("sentiment_spike", 0),
    ],
}
if earnings_days is not None:
    sig_data["Signal"].append("Earnings Proximity")
    sig_data["Value"].append(f"{earnings_days}d away")
    sig_data["Triggered"].append("✅" if result["breakdown"].get("earnings_proximity", 0) > 0 else "—")
    sig_data["Points"].append(result["breakdown"].get("earnings_proximity", 0))

import pandas as pd
st.dataframe(pd.DataFrame(sig_data), use_container_width=True, hide_index=True)

st.divider()

# ── Charts ────────────────────────────────────────────────────────────────────
st.subheader("Charts")

# Candlestick + BB
bbands = ta.bbands(df["Close"], length=20)
rsi_series = ta.rsi(df["Close"], length=14)
atr_series = ta.atr(df["High"], df["Low"], df["Close"], length=14)

fig = sp.make_subplots(
    rows=3, cols=1,
    shared_xaxes=True,
    row_heights=[0.55, 0.25, 0.20],
    vertical_spacing=0.03,
    subplot_titles=[f"{ticker} Price + BB Bands", "RSI (14)", "ATR (14)"],
)

fig.add_trace(go.Candlestick(
    x=df.index, open=df["Open"], high=df["High"],
    low=df["Low"], close=df["Close"], name="Price",
), row=1, col=1)

if bbands is not None and not bbands.empty:
    upper_col = [c for c in bbands.columns if "BBU" in c]
    lower_col = [c for c in bbands.columns if "BBL" in c]
    mid_col = [c for c in bbands.columns if "BBM" in c]
    if upper_col and lower_col and mid_col:
        fig.add_trace(go.Scatter(x=df.index, y=bbands[upper_col[0]], name="BB Upper",
                                  line=dict(color="#93c5fd", dash="dot", width=1)), row=1, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=bbands[mid_col[0]], name="BB Mid",
                                  line=dict(color="#60a5fa", dash="dot", width=1)), row=1, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=bbands[lower_col[0]], name="BB Lower",
                                  line=dict(color="#93c5fd", dash="dot", width=1),
                                  fill="tonexty", fillcolor="rgba(147,197,253,0.06)"), row=1, col=1)

if rsi_series is not None:
    fig.add_trace(go.Scatter(x=df.index, y=rsi_series, name="RSI",
                              line=dict(color="#a78bfa")), row=2, col=1)
    fig.add_hline(y=70, line_dash="dot", line_color="#dc2626", row=2, col=1)
    fig.add_hline(y=30, line_dash="dot", line_color="#16a34a", row=2, col=1)

if atr_series is not None:
    fig.add_trace(go.Scatter(x=df.index, y=atr_series, name="ATR",
                              line=dict(color="#f59e0b"), fill="tozeroy",
                              fillcolor="rgba(245,158,11,0.1)"), row=3, col=1)

fig.update_layout(
    height=700,
    template="plotly_white",
    xaxis_rangeslider_visible=False,
    showlegend=False,
)
st.plotly_chart(fig, use_container_width=True)

st.divider()

# ── Claude explanation ─────────────────────────────────────────────────────────
st.subheader("AI Analysis")
st.caption("Claude Sonnet — streaming explanation of this setup")

if st.button("Generate Analysis", type="secondary"):
    from analyst.claude_analyst import stream_explanation
    with st.chat_message("assistant"):
        st.write_stream(stream_explanation(result))
