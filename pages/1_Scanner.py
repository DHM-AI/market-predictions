import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime

st.set_page_config(page_title="Scanner", page_icon="🔍", layout="wide")
st.title("Scanner")
st.caption("Scans S&P 500 + futures for 5-10%+ move setups.")

# ── Run Scan ──────────────────────────────────────────────────────────────────
col_btn, col_info = st.columns([1, 3])
with col_btn:
    run_clicked = st.button("Run Scan Now", type="primary", use_container_width=True)
with col_info:
    from model.predictor import model_available
    if model_available():
        st.success("XGBoost model loaded")
    else:
        st.warning("No trained model found — using rule-based scorer. Run `python -m model.trainer` first.")

if run_clicked:
    with st.spinner("Running full universe scan (this takes a few minutes)..."):
        from agent import run_scan
        picks_df = run_scan(send_email=False, verbose=False)
        if picks_df is not None and not picks_df.empty:
            st.session_state["last_picks"] = picks_df
            st.session_state["scan_time"] = datetime.now().strftime("%Y-%m-%d %H:%M")
        else:
            st.info("No setups above threshold in today's scan.")

# ── Load last scan from session or CSV log ────────────────────────────────────
picks_df = st.session_state.get("last_picks")
scan_time = st.session_state.get("scan_time", "")

if picks_df is None:
    today_str = datetime.today().strftime("%Y-%m-%d")
    try:
        from db import load_predictions_for_date, db_available
        if db_available():
            rows = load_predictions_for_date(today_str)
            if rows:
                picks_df = pd.DataFrame(rows)
                scan_time = today_str
    except Exception:
        pass

if picks_df is None or picks_df.empty:
    st.info("No scan results yet. Click **Run Scan Now** to start.")
    st.stop()

# ── Summary metrics ───────────────────────────────────────────────────────────
st.divider()
if scan_time:
    st.caption(f"Last scan: {scan_time}")

m1, m2, m3, m4 = st.columns(4)
m1.metric("Total Setups", len(picks_df))
high_conf = picks_df[picks_df["confidence"] == "High"] if "confidence" in picks_df.columns else pd.DataFrame()
m2.metric("High Confidence", len(high_conf))
bull = (picks_df["direction"] == "bullish").sum() if "direction" in picks_df.columns else 0
bear = (picks_df["direction"] == "bearish").sum() if "direction" in picks_df.columns else 0
m3.metric("Bullish / Bearish", f"{bull} / {bear}")
avg_score = round(picks_df["score"].mean(), 1) if "score" in picks_df.columns else 0
m4.metric("Avg Score", avg_score)

# ── Results table ─────────────────────────────────────────────────────────────
st.subheader("Flagged Setups")

display_cols = [c for c in ["ticker", "score", "direction", "confidence", "duration",
                             "rsi", "volume_ratio", "sentiment_score", "earnings_days"]
                if c in picks_df.columns]
display_df = picks_df[display_cols].copy()

def color_direction(val):
    if val == "bullish":
        return "color: #16a34a; font-weight: bold"
    if val == "bearish":
        return "color: #dc2626; font-weight: bold"
    return ""

def color_score(val):
    if val >= 70:
        return "background-color: #dcfce7"
    if val >= 50:
        return "background-color: #fef9c3"
    return ""

styled = display_df.style
if "direction" in display_df.columns:
    styled = styled.map(color_direction, subset=["direction"])
if "score" in display_df.columns:
    styled = styled.map(color_score, subset=["score"])

st.dataframe(styled, use_container_width=True, height=400)

# ── Per-ticker chart ──────────────────────────────────────────────────────────
st.divider()
st.subheader("Ticker Chart")
tickers = picks_df["ticker"].tolist()
selected = st.selectbox("Select ticker to chart", tickers)

if selected:
    from data.fetcher import get_ohlcv
    import pandas_ta as ta

    df = get_ohlcv(selected, period="6mo")
    if df.empty:
        st.warning(f"No price data for {selected}")
    else:
        bbands = ta.bbands(df["Close"], length=20)
        fig = go.Figure()
        fig.add_trace(go.Candlestick(
            x=df.index, open=df["Open"], high=df["High"],
            low=df["Low"], close=df["Close"], name=selected,
        ))
        if bbands is not None and not bbands.empty:
            upper_col = [c for c in bbands.columns if "BBU" in c]
            lower_col = [c for c in bbands.columns if "BBL" in c]
            mid_col = [c for c in bbands.columns if "BBM" in c]
            if upper_col and lower_col and mid_col:
                fig.add_trace(go.Scatter(x=df.index, y=bbands[upper_col[0]],
                                         name="BB Upper", line=dict(color="#93c5fd", dash="dot")))
                fig.add_trace(go.Scatter(x=df.index, y=bbands[mid_col[0]],
                                         name="BB Mid", line=dict(color="#60a5fa", dash="dot")))
                fig.add_trace(go.Scatter(x=df.index, y=bbands[lower_col[0]],
                                         name="BB Lower", line=dict(color="#93c5fd", dash="dot"),
                                         fill="tonexty", fillcolor="rgba(147,197,253,0.05)"))

        fig.update_layout(
            title=f"{selected} — 6 Month Price + Bollinger Bands",
            xaxis_rangeslider_visible=False,
            height=450,
            template="plotly_white",
        )
        st.plotly_chart(fig, use_container_width=True)

        # Volume subplot
        vol_fig = go.Figure()
        vol_fig.add_trace(go.Bar(x=df.index, y=df["Volume"], name="Volume",
                                  marker_color="#60a5fa"))
        avg_vol = df["Volume"].rolling(20).mean()
        vol_fig.add_trace(go.Scatter(x=df.index, y=avg_vol, name="20d Avg",
                                      line=dict(color="#f97316")))
        vol_fig.update_layout(title="Volume", height=200, template="plotly_white",
                               showlegend=True)
        st.plotly_chart(vol_fig, use_container_width=True)

        # Show signals for selected ticker
        row = picks_df[picks_df["ticker"] == selected].iloc[0]
        signals = row.get("signals_triggered", [])
        if isinstance(signals, str):
            signals = [s.strip() for s in signals.split(";") if s.strip()]
        if signals:
            st.markdown("**Signals triggered:** " + " · ".join(f"`{s}`" for s in signals))
