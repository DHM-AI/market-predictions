import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
from ui_style import inject_css, live_badge, section_header, score_pill, direction_badge, agent_card

st.set_page_config(page_title="Scanner", page_icon="🔍", layout="wide")
inject_css()

st.markdown(
    f'<h2 style="color:#e8e8e8;font-weight:700;">Scanner{live_badge()}</h2>'
    f'<p style="color:#444;font-size:13px;margin-top:-8px;">S&P 500 + Futures · 5-agent pipeline · 5-10% move detection</p>',
    unsafe_allow_html=True
)

# ── Run scan button ────────────────────────────────────────────────────────────
col_btn, col_model = st.columns([1, 3])
with col_btn:
    run_clicked = st.button("▶  Run Scan", type="primary", use_container_width=True)
with col_model:
    from model.predictor import model_available
    if model_available():
        st.markdown('<span style="color:#00ff88;font-size:13px;">● XGBoost model loaded</span>', unsafe_allow_html=True)
    else:
        st.markdown('<span style="color:#f59e0b;font-size:13px;">⚠ No model — run `python -m model.trainer` first (rule-based fallback active)</span>', unsafe_allow_html=True)

if run_clicked:
    # Show pipeline progress
    section_header("PIPELINE RUNNING")
    p1 = st.markdown(agent_card("1 · Scan Agent", "Fetching OHLCV for 509 tickers...", "…", "running"), unsafe_allow_html=True)
    p2 = st.markdown(agent_card("2 · Research Agent", "Reddit + RSS + news sentiment", "…", "idle"), unsafe_allow_html=True)
    p3 = st.markdown(agent_card("3 · Predict Agent", "XGBoost scoring", "…", "idle"), unsafe_allow_html=True)
    p4 = st.markdown(agent_card("4 · Risk Agent", "Kelly Criterion sizing", "…", "idle"), unsafe_allow_html=True)
    p5 = st.markdown(agent_card("5 · Learn Agent", "Backfilling actuals", "…", "idle"), unsafe_allow_html=True)

    with st.spinner("Running full scan — takes 3-5 min..."):
        from agent import run_scan
        picks_df = run_scan(send_email=False, execute_trades=False, verbose=False)
        if picks_df is not None and not picks_df.empty:
            st.session_state["last_picks"] = picks_df
            st.session_state["scan_time"] = datetime.now().strftime("%Y-%m-%d %H:%M")
        else:
            st.info("No setups above threshold today.")

# ── Load results ───────────────────────────────────────────────────────────────
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
    st.markdown('<div style="color:#444;text-align:center;padding:60px 0;">No scan results yet — click Run Scan to start</div>', unsafe_allow_html=True)
    st.stop()

st.divider()

# ── Metrics bar ────────────────────────────────────────────────────────────────
if scan_time:
    st.markdown(f'<div style="color:#444;font-size:11px;text-transform:uppercase;letter-spacing:1px;">Last scan: {scan_time}</div>', unsafe_allow_html=True)

m1, m2, m3, m4, m5 = st.columns(5)
m1.metric("Setups Found", len(picks_df))
high = len(picks_df[picks_df.get("confidence", pd.Series()) == "High"]) if "confidence" in picks_df else 0
m2.metric("High Confidence", high)
bull = (picks_df["direction"] == "bullish").sum() if "direction" in picks_df else 0
bear = (picks_df["direction"] == "bearish").sum() if "direction" in picks_df else 0
m3.metric("Bullish", bull)
m4.metric("Bearish", bear)
avg_score = round(picks_df["score"].mean(), 1) if "score" in picks_df else 0
m5.metric("Avg Score", avg_score)

# ── Results table (custom HTML) ────────────────────────────────────────────────
st.divider()
section_header("FLAGGED SETUPS")

rows_html = ""
for _, row in picks_df.iterrows():
    score   = row.get("score", 0)
    ticker  = row.get("ticker", "")
    direct  = row.get("direction", "mixed")
    dur     = row.get("duration", "—")
    conf    = row.get("confidence", "—")
    rsi     = row.get("rsi", "—")
    vol_r   = row.get("volume_ratio", "—")
    kelly   = row.get("dollar_amount", 0)
    risk_lv = row.get("risk_level", "—")

    conf_color = {"High": "#00ff88", "Medium": "#f59e0b", "Low": "#555"}.get(conf, "#555")
    dir_html   = direction_badge(direct)
    score_html = score_pill(score)
    kelly_str  = f"${kelly:,.0f}" if kelly else "—"

    rows_html += f"""
    <tr style="border-bottom:1px solid #1a1a1a;">
      <td style="padding:10px 12px;font-family:'JetBrains Mono',monospace;font-weight:700;color:#e8e8e8;">{ticker}</td>
      <td style="padding:10px 12px;">{score_html}</td>
      <td style="padding:10px 12px;">{dir_html}</td>
      <td style="padding:10px 12px;color:#555;font-size:12px;">{dur}</td>
      <td style="padding:10px 12px;color:{conf_color};font-size:12px;font-weight:600;">{conf}</td>
      <td style="padding:10px 12px;font-family:'JetBrains Mono',monospace;color:#e8e8e8;">{rsi}</td>
      <td style="padding:10px 12px;font-family:'JetBrains Mono',monospace;color:#e8e8e8;">{vol_r if isinstance(vol_r, str) else f'{vol_r:.1f}x'}</td>
      <td style="padding:10px 12px;font-family:'JetBrains Mono',monospace;color:#00ff88;font-weight:600;">{kelly_str}</td>
    </tr>
    """

st.markdown(f"""
<table width="100%" cellpadding="0" cellspacing="0"
       style="border-collapse:collapse;background:#0d0d0d;border:1px solid #1e1e1e;border-radius:6px;overflow:hidden;">
  <thead>
    <tr style="background:#111;">
      <th style="padding:10px 12px;text-align:left;color:#444;font-size:11px;letter-spacing:1px;text-transform:uppercase;">Ticker</th>
      <th style="padding:10px 12px;text-align:left;color:#444;font-size:11px;letter-spacing:1px;text-transform:uppercase;">Score</th>
      <th style="padding:10px 12px;text-align:left;color:#444;font-size:11px;letter-spacing:1px;text-transform:uppercase;">Direction</th>
      <th style="padding:10px 12px;text-align:left;color:#444;font-size:11px;letter-spacing:1px;text-transform:uppercase;">Window</th>
      <th style="padding:10px 12px;text-align:left;color:#444;font-size:11px;letter-spacing:1px;text-transform:uppercase;">Confidence</th>
      <th style="padding:10px 12px;text-align:left;color:#444;font-size:11px;letter-spacing:1px;text-transform:uppercase;">RSI</th>
      <th style="padding:10px 12px;text-align:left;color:#444;font-size:11px;letter-spacing:1px;text-transform:uppercase;">Vol Ratio</th>
      <th style="padding:10px 12px;text-align:left;color:#444;font-size:11px;letter-spacing:1px;text-transform:uppercase;">Kelly Size</th>
    </tr>
  </thead>
  <tbody>{rows_html}</tbody>
</table>
""", unsafe_allow_html=True)

# ── Chart ──────────────────────────────────────────────────────────────────────
st.divider()
section_header("PRICE CHART")
tickers = picks_df["ticker"].tolist()
selected = st.selectbox("Select ticker", tickers, label_visibility="collapsed")

if selected:
    from data.fetcher import get_ohlcv
    import pandas_ta as ta
    df = get_ohlcv(selected, period="6mo")
    if not df.empty:
        bbands = ta.bbands(df["Close"], length=20)
        fig = go.Figure()
        fig.add_trace(go.Candlestick(
            x=df.index, open=df["Open"], high=df["High"],
            low=df["Low"], close=df["Close"], name=selected,
            increasing=dict(line=dict(color="#00ff88"), fillcolor="#00ff8833"),
            decreasing=dict(line=dict(color="#ef4444"), fillcolor="#ef444433"),
        ))
        if bbands is not None and not bbands.empty:
            u = [c for c in bbands.columns if "BBU" in c]
            l = [c for c in bbands.columns if "BBL" in c]
            m = [c for c in bbands.columns if "BBM" in c]
            if u and l and m:
                fig.add_trace(go.Scatter(x=df.index, y=bbands[u[0]], name="BB Upper",
                    line=dict(color="#333", width=1, dash="dot")))
                fig.add_trace(go.Scatter(x=df.index, y=bbands[m[0]], name="BB Mid",
                    line=dict(color="#444", width=1, dash="dot")))
                fig.add_trace(go.Scatter(x=df.index, y=bbands[l[0]], name="BB Lower",
                    line=dict(color="#333", width=1, dash="dot"),
                    fill="tonexty", fillcolor="rgba(255,255,255,0.02)"))
        fig.update_layout(
            xaxis_rangeslider_visible=False,
            height=400, template="plotly_dark",
            paper_bgcolor="#0d0d0d", plot_bgcolor="#0d0d0d",
            xaxis=dict(gridcolor="#1a1a1a", showgrid=True),
            yaxis=dict(gridcolor="#1a1a1a", showgrid=True),
            font=dict(color="#555"),
            margin=dict(l=0, r=0, t=20, b=0),
            legend=dict(bgcolor="#0d0d0d", bordercolor="#1e1e1e"),
        )
        st.plotly_chart(fig, use_container_width=True)

        row = picks_df[picks_df["ticker"] == selected].iloc[0]
        sigs = row.get("signals_triggered", [])
        if isinstance(sigs, str):
            sigs = [s.strip() for s in sigs.split(";") if s.strip()]
        if sigs:
            st.markdown(
                '<div style="margin-top:8px;">' +
                "".join(f'<span style="display:inline-block;background:#161616;border:1px solid #1e1e1e;'
                        f'color:#00ff88;font-size:11px;padding:3px 8px;border-radius:3px;margin:2px;">{s}</span>'
                        for s in sigs) +
                '</div>', unsafe_allow_html=True
            )
