import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from ui_style import inject_css, section_header, live_badge
from config import MOVE_TARGET_PCT

st.set_page_config(page_title="Track Record", page_icon="📋", layout="wide")
inject_css()

st.markdown(
    f'<h2 style="color:#e8e8e8;font-weight:700;">Track Record{live_badge()}</h2>'
    f'<p style="color:#444;font-size:13px;margin-top:-8px;">Prediction accuracy · Hit rate · Score calibration</p>',
    unsafe_allow_html=True
)

try:
    from db import load_predictions, db_available
    if not db_available():
        st.markdown('<div style="color:#f59e0b;padding:20px;background:#161616;border:1px solid #1e1e1e;border-radius:6px;">'
                    '⚠ Supabase not configured. Add SUPABASE_URL and SUPABASE_KEY to your .env</div>',
                    unsafe_allow_html=True)
        st.stop()
    rows = load_predictions()
except Exception as e:
    st.error(f"Could not load predictions: {e}")
    st.stop()

if not rows:
    st.markdown('<div style="color:#333;text-align:center;padding:80px 0;">No predictions yet — run a scan first</div>', unsafe_allow_html=True)
    st.stop()

log = pd.DataFrame(rows)
log["date"] = pd.to_datetime(log["date"])
log = log.sort_values("date", ascending=False)

# ── Filters ────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown('<div style="color:#444;font-size:11px;letter-spacing:1px;text-transform:uppercase;margin-bottom:12px;">Filters</div>', unsafe_allow_html=True)
    min_date = log["date"].min().date()
    max_date = log["date"].max().date()
    date_range = st.date_input("Date range", value=(min_date, max_date), min_value=min_date, max_value=max_date)
    direction_filter = st.multiselect("Direction", ["bullish","bearish","mixed"], default=["bullish","bearish","mixed"])
    confidence_filter = st.multiselect("Confidence", ["High","Medium","Low"], default=["High","Medium","Low"])

filtered = log.copy()
if len(date_range) == 2:
    filtered = filtered[(filtered["date"].dt.date >= date_range[0]) & (filtered["date"].dt.date <= date_range[1])]
if direction_filter:
    filtered = filtered[filtered["direction"].isin(direction_filter)]
if confidence_filter and "confidence" in filtered.columns:
    filtered = filtered[filtered["confidence"].isin(confidence_filter)]

evaluated = filtered[filtered["actual_move_5d"].notna()].copy() if "actual_move_5d" in filtered.columns else pd.DataFrame()
if not evaluated.empty:
    evaluated["hit"] = evaluated["actual_move_5d"].abs() >= (MOVE_TARGET_PCT * 100)

# ── Metrics ────────────────────────────────────────────────────────────────────
st.divider()
section_header("PERFORMANCE SUMMARY")
m1, m2, m3, m4, m5 = st.columns(5)
m1.metric("Total Predictions", len(filtered))
m2.metric("Evaluated", len(evaluated))
if not evaluated.empty and len(evaluated) > 0:
    hit_rate = evaluated["hit"].mean() * 100
    avg_move = evaluated["actual_move_5d"].abs().mean()
    best     = evaluated["actual_move_5d"].abs().max()
    m3.metric("Hit Rate", f"{hit_rate:.1f}%")
    m4.metric("Avg Move", f"{avg_move:.1f}%")
    m5.metric("Best Move", f"{best:.1f}%")

# ── Charts ─────────────────────────────────────────────────────────────────────
if not evaluated.empty and len(evaluated) > 5:
    st.divider()
    c1, c2 = st.columns(2)

    with c1:
        section_header("HIT RATE BY CONFIDENCE")
        if "confidence" in evaluated.columns:
            conf_stats = evaluated.groupby("confidence").agg(hit_rate=("hit","mean")).reset_index()
            conf_stats["hit_rate_pct"] = conf_stats["hit_rate"] * 100
            color_map = {"High": "#00ff88", "Medium": "#f59e0b", "Low": "#555"}
            fig = px.bar(conf_stats, x="confidence", y="hit_rate_pct", color="confidence",
                         color_discrete_map=color_map, text="hit_rate_pct")
            fig.update_traces(texttemplate="%{text:.1f}%", textposition="outside", textfont_color="#e8e8e8")
            fig.update_layout(template="plotly_dark", paper_bgcolor="#161616",
                              plot_bgcolor="#161616", showlegend=False, height=280,
                              margin=dict(l=0,r=0,t=10,b=0),
                              yaxis=dict(gridcolor="#1e1e1e"),
                              xaxis=dict(title=""), yaxis_title="Hit Rate (%)")
            st.plotly_chart(fig, use_container_width=True)

    with c2:
        section_header("SCORE vs ACTUAL MOVE")
        if "score" in evaluated.columns:
            fig2 = px.scatter(evaluated, x="score", y="actual_move_5d",
                              color="hit", color_discrete_map={True:"#00ff88", False:"#ef4444"},
                              hover_data=["ticker","date","direction"])
            fig2.add_hline(y=5, line_dash="dot", line_color="#00ff8866")
            fig2.add_hline(y=-5, line_dash="dot", line_color="#ef444466")
            fig2.update_layout(template="plotly_dark", paper_bgcolor="#161616",
                               plot_bgcolor="#161616", showlegend=False, height=280,
                               margin=dict(l=0,r=0,t=10,b=0),
                               yaxis=dict(gridcolor="#1e1e1e"),
                               xaxis=dict(gridcolor="#1e1e1e"))
            st.plotly_chart(fig2, use_container_width=True)

# ── Full log table ─────────────────────────────────────────────────────────────
st.divider()
section_header("PREDICTION LOG")

show_cols = [c for c in ["date","ticker","score","direction","confidence","duration","actual_move_5d"] if c in filtered.columns]
display = filtered[show_cols].copy()
display["date"] = display["date"].dt.strftime("%Y-%m-%d")

rows_html = ""
for _, row in display.iterrows():
    move = row.get("actual_move_5d", None)
    if pd.isna(move) if move is not None else True:
        move_str = '<span style="color:#333;">Pending</span>'
    else:
        color = "#00ff88" if abs(move) >= 5 else "#555"
        arrow = "▲" if move > 0 else "▼"
        move_str = f'<span style="color:{color};font-family:JetBrains Mono,monospace;">{arrow} {abs(move):.1f}%</span>'

    dir_ = row.get("direction","")
    dir_color = {"bullish":"#00ff88","bearish":"#ef4444"}.get(dir_,"#555")
    score_ = row.get("score", 0)
    score_color = "#00ff88" if score_ >= 70 else "#f59e0b" if score_ >= 50 else "#555"
    conf_ = row.get("confidence","")
    conf_color = {"High":"#00ff88","Medium":"#f59e0b","Low":"#555"}.get(conf_,"#555")

    rows_html += f"""<tr style="border-bottom:1px solid #1a1a1a;">
      <td style="padding:8px 12px;color:#555;font-size:12px;">{row.get('date','')}</td>
      <td style="padding:8px 12px;font-family:JetBrains Mono,monospace;font-weight:700;color:#e8e8e8;">{row.get('ticker','')}</td>
      <td style="padding:8px 12px;font-family:JetBrains Mono,monospace;color:{score_color};">{score_}</td>
      <td style="padding:8px 12px;color:{dir_color};font-weight:600;font-size:12px;">{dir_.upper()}</td>
      <td style="padding:8px 12px;color:{conf_color};font-size:12px;">{conf_}</td>
      <td style="padding:8px 12px;color:#555;font-size:12px;">{row.get('duration','')}</td>
      <td style="padding:8px 12px;">{move_str}</td>
    </tr>"""

st.markdown(f"""
<div style="overflow-y:auto;max-height:500px;border:1px solid #1e1e1e;border-radius:6px;">
<table width="100%" cellpadding="0" cellspacing="0" style="border-collapse:collapse;background:#0d0d0d;">
  <thead style="position:sticky;top:0;z-index:1;">
    <tr style="background:#111;">
      {"".join(f'<th style="padding:10px 12px;text-align:left;color:#444;font-size:11px;letter-spacing:1px;text-transform:uppercase;">{h}</th>' for h in ["Date","Ticker","Score","Direction","Confidence","Window","Actual Move"])}
    </tr>
  </thead>
  <tbody>{rows_html}</tbody>
</table>
</div>
""", unsafe_allow_html=True)

st.download_button("⬇ Export CSV", filtered.to_csv(index=False),
                   file_name="predictions.csv", mime="text/csv")
