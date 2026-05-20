import streamlit as st
import plotly.graph_objects as go
import plotly.subplots as sp
import pandas_ta as ta
from ui_style import inject_css, section_header, score_pill, direction_badge, live_badge

st.set_page_config(page_title="Ticker Deep Dive", page_icon="📊", layout="wide")
inject_css()

st.markdown(
    f'<h2 style="color:#e8e8e8;font-weight:700;">Ticker Deep Dive{live_badge()}</h2>'
    f'<p style="color:#444;font-size:13px;margin-top:-8px;">Full signal breakdown + AI analysis for any ticker</p>',
    unsafe_allow_html=True
)

col_in, col_btn = st.columns([3, 1])
with col_in:
    ticker_input = st.text_input("", placeholder="Enter symbol — AAPL, TSLA, ES=F, NQ=F ...",
                                  label_visibility="collapsed")
with col_btn:
    analyze = st.button("Analyze", type="primary", use_container_width=True)

if not ticker_input or not analyze:
    st.markdown('<div style="color:#333;text-align:center;padding:80px 0;font-size:13px;">Enter a ticker above to analyze</div>', unsafe_allow_html=True)
    st.stop()

ticker = ticker_input.upper().strip()

with st.spinner(f"Analyzing {ticker}..."):
    from data.fetcher import get_ohlcv, get_earnings_days
    from signals.technicals import compute_all
    from signals.sentiment import get_sentiment_with_velocity
    from signals.scorer import score_ticker

    df = get_ohlcv(ticker, period="1y")
    if df.empty:
        st.error(f"No data found for {ticker}")
        st.stop()

    sentiment  = get_sentiment_with_velocity(ticker)
    earnings   = get_earnings_days(ticker)
    technicals = compute_all(df)
    result     = score_ticker(ticker, df, sentiment, earnings)

# ── Score header ───────────────────────────────────────────────────────────────
st.divider()
c1, c2, c3, c4 = st.columns(4)
score = result.get("score", 0)
c1.markdown(f'<div style="background:#161616;border:1px solid #1e1e1e;border-radius:6px;padding:18px;text-align:center;">'
            f'<div style="color:#444;font-size:11px;text-transform:uppercase;letter-spacing:1px;">Score</div>'
            f'<div style="font-family:JetBrains Mono,monospace;font-size:36px;font-weight:700;color:{"#00ff88" if score>=70 else "#f59e0b" if score>=50 else "#555"};">{score}</div>'
            f'<div style="color:#444;font-size:11px;">/ 100</div></div>', unsafe_allow_html=True)
c2.markdown(f'<div style="background:#161616;border:1px solid #1e1e1e;border-radius:6px;padding:18px;text-align:center;">'
            f'<div style="color:#444;font-size:11px;text-transform:uppercase;letter-spacing:1px;">Direction</div>'
            f'<div style="font-size:20px;font-weight:700;margin-top:8px;">{direction_badge(result.get("direction","mixed"))}</div>'
            f'</div>', unsafe_allow_html=True)
c3.markdown(f'<div style="background:#161616;border:1px solid #1e1e1e;border-radius:6px;padding:18px;text-align:center;">'
            f'<div style="color:#444;font-size:11px;text-transform:uppercase;letter-spacing:1px;">Window</div>'
            f'<div style="color:#e8e8e8;font-size:15px;font-weight:600;margin-top:8px;">{result.get("duration","—")}</div>'
            f'</div>', unsafe_allow_html=True)
conf = result.get("confidence","—")
conf_color = {"High":"#00ff88","Medium":"#f59e0b","Low":"#555"}.get(conf,"#555")
c4.markdown(f'<div style="background:#161616;border:1px solid #1e1e1e;border-radius:6px;padding:18px;text-align:center;">'
            f'<div style="color:#444;font-size:11px;text-transform:uppercase;letter-spacing:1px;">Confidence</div>'
            f'<div style="color:{conf_color};font-size:20px;font-weight:700;margin-top:8px;">● {conf}</div>'
            f'</div>', unsafe_allow_html=True)

# Signal tags
sigs = result.get("signals_triggered", [])
if sigs:
    st.markdown('<div style="margin:12px 0;">' +
        "".join(f'<span style="display:inline-block;background:#161616;border:1px solid #00ff88;color:#00ff88;'
                f'font-size:11px;padding:3px 10px;border-radius:3px;margin:3px;">{s}</span>' for s in sigs) +
        '</div>', unsafe_allow_html=True)

# ── Signal breakdown ───────────────────────────────────────────────────────────
st.divider()
section_header("SIGNAL BREAKDOWN")

signals_data = [
    ("BB Squeeze",     technicals["bb"]["triggered"],  f"Width pct: {technicals['bb']['width_percentile']}"),
    ("ATR Compression",technicals["atr"]["triggered"], f"Ratio: {technicals['atr']['ratio']}"),
    ("Volume Surge",   technicals["vol"]["triggered"],  f"{technicals['vol']['ratio']}x avg"),
    ("RSI Extreme",    technicals["rsi"]["extreme"],    f"RSI {technicals['rsi']['value']} ({technicals['rsi']['side']})"),
    ("Sentiment Spike",sentiment.get("spike", False),  f"Score {sentiment.get('score',0):.3f} Δ{sentiment.get('velocity',0):.3f}"),
]
if earnings is not None:
    from config import EARNINGS_PROXIMITY_DAYS
    signals_data.append(("Earnings Proximity", 0 <= earnings <= EARNINGS_PROXIMITY_DAYS, f"{earnings}d away"))

cols = st.columns(len(signals_data))
for i, (name, triggered, detail) in enumerate(signals_data):
    color  = "#00ff88" if triggered else "#333"
    icon   = "●" if triggered else "○"
    pts    = result["breakdown"].get(name.lower().replace(" ","_"), 0)
    cols[i].markdown(
        f'<div style="background:#161616;border:1px solid #1e1e1e;border-left:3px solid {color};'
        f'border-radius:6px;padding:12px;text-align:center;">'
        f'<div style="color:{color};font-size:18px;">{icon}</div>'
        f'<div style="color:#e8e8e8;font-size:12px;font-weight:600;margin:4px 0;">{name}</div>'
        f'<div style="color:#555;font-size:11px;">{detail}</div>'
        f'<div style="color:{color};font-size:11px;margin-top:4px;">+{pts} pts</div>'
        f'</div>', unsafe_allow_html=True
    )

# ── Chart ──────────────────────────────────────────────────────────────────────
st.divider()
section_header("CHARTS")

rsi_s = ta.rsi(df["Close"], length=14)
atr_s = ta.atr(df["High"], df["Low"], df["Close"], length=14)
bbands = ta.bbands(df["Close"], length=20)

fig = sp.make_subplots(rows=3, cols=1, shared_xaxes=True,
                       row_heights=[0.55, 0.25, 0.20], vertical_spacing=0.03)

fig.add_trace(go.Candlestick(x=df.index, open=df["Open"], high=df["High"],
    low=df["Low"], close=df["Close"], name=ticker,
    increasing=dict(line=dict(color="#00ff88"), fillcolor="#00ff8833"),
    decreasing=dict(line=dict(color="#ef4444"), fillcolor="#ef444433")), row=1, col=1)

if bbands is not None and not bbands.empty:
    u = [c for c in bbands.columns if "BBU" in c]
    l = [c for c in bbands.columns if "BBL" in c]
    m = [c for c in bbands.columns if "BBM" in c]
    if u and l and m:
        fig.add_trace(go.Scatter(x=df.index, y=bbands[u[0]], line=dict(color="#1e1e1e", width=1),
                                  name="BB Upper", showlegend=False), row=1, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=bbands[l[0]], line=dict(color="#1e1e1e", width=1),
                                  name="BB Lower", fill="tonexty",
                                  fillcolor="rgba(255,255,255,0.02)", showlegend=False), row=1, col=1)

if rsi_s is not None:
    fig.add_trace(go.Scatter(x=df.index, y=rsi_s, line=dict(color="#a78bfa", width=1.5),
                              name="RSI"), row=2, col=1)
    fig.add_hline(y=72, line_dash="dot", line_color="#ef4444", row=2, col=1)
    fig.add_hline(y=28, line_dash="dot", line_color="#00ff88", row=2, col=1)

if atr_s is not None:
    fig.add_trace(go.Scatter(x=df.index, y=atr_s, line=dict(color="#f59e0b", width=1.5),
                              fill="tozeroy", fillcolor="rgba(245,158,11,0.05)",
                              name="ATR"), row=3, col=1)

fig.update_layout(height=600, template="plotly_dark",
                  paper_bgcolor="#0d0d0d", plot_bgcolor="#0d0d0d",
                  xaxis_rangeslider_visible=False,
                  xaxis3=dict(gridcolor="#1a1a1a"),
                  yaxis=dict(gridcolor="#1a1a1a"),
                  yaxis2=dict(gridcolor="#1a1a1a"),
                  yaxis3=dict(gridcolor="#1a1a1a"),
                  margin=dict(l=0, r=0, t=10, b=0), showlegend=False)
st.plotly_chart(fig, use_container_width=True)

# ── AI Analysis ────────────────────────────────────────────────────────────────
st.divider()
section_header("AI ANALYSIS")

if st.button("Generate Claude Analysis", type="primary"):
    from analyst.claude_analyst import stream_explanation
    st.markdown('<div style="background:#161616;border:1px solid #1e1e1e;border-radius:6px;padding:16px;">', unsafe_allow_html=True)
    with st.chat_message("assistant"):
        st.write_stream(stream_explanation(result))
    st.markdown('</div>', unsafe_allow_html=True)
