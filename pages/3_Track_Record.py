import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from config import MOVE_TARGET_PCT

st.set_page_config(page_title="Track Record", page_icon="📋", layout="wide")
st.title("Track Record")
st.caption("Historical prediction log — accuracy, calibration, and hit rate over time.")

try:
    from db import load_predictions, db_available
    if not db_available():
        st.warning("Supabase not configured. Add SUPABASE_URL and SUPABASE_KEY to your .env file.")
        st.stop()
    rows = load_predictions()
except Exception as e:
    st.error(f"Could not load predictions from Supabase: {e}")
    st.stop()

if not rows:
    st.info("No prediction log found yet. Run a scan first.")
    st.stop()

log = pd.DataFrame(rows)
if log.empty:
    st.info("Prediction log is empty.")
    st.stop()

log["date"] = pd.to_datetime(log["date"])
log = log.sort_values("date", ascending=False)

# ── Filters ────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.header("Filters")
    min_date = log["date"].min().date()
    max_date = log["date"].max().date()
    date_range = st.date_input("Date range", value=(min_date, max_date),
                                min_value=min_date, max_value=max_date)
    direction_filter = st.multiselect("Direction", options=["bullish", "bearish", "mixed"],
                                       default=["bullish", "bearish", "mixed"])
    confidence_filter = st.multiselect("Confidence", options=["High", "Medium", "Low"],
                                        default=["High", "Medium", "Low"])

filtered = log.copy()
if len(date_range) == 2:
    filtered = filtered[(filtered["date"].dt.date >= date_range[0]) &
                        (filtered["date"].dt.date <= date_range[1])]
if direction_filter:
    filtered = filtered[filtered["direction"].isin(direction_filter)]
if confidence_filter and "confidence" in filtered.columns:
    filtered = filtered[filtered["confidence"].isin(confidence_filter)]

# ── Evaluated predictions (actual_move_5d filled in) ─────────────────────────
evaluated = filtered[filtered["actual_move_5d"].notna()].copy()
evaluated["hit"] = evaluated["actual_move_5d"].abs() >= (MOVE_TARGET_PCT * 100)

# ── Summary metrics ───────────────────────────────────────────────────────────
m1, m2, m3, m4, m5 = st.columns(5)
m1.metric("Total Predictions", len(filtered))
m2.metric("Evaluated", len(evaluated))

if len(evaluated) > 0:
    hit_rate = evaluated["hit"].mean() * 100
    avg_move = evaluated["actual_move_5d"].abs().mean()
    best_move = evaluated["actual_move_5d"].abs().max()
    m3.metric("Hit Rate", f"{hit_rate:.1f}%")
    m4.metric("Avg Move", f"{avg_move:.1f}%")
    m5.metric("Best Move", f"{best_move:.1f}%")
else:
    m3.metric("Hit Rate", "N/A")
    m4.metric("Avg Move", "N/A")
    m5.metric("Best Move", "N/A")
    st.info("No evaluated predictions yet — actual_move_5d is filled automatically after 5 trading days.")

st.divider()

# ── Hit rate by confidence ─────────────────────────────────────────────────────
if len(evaluated) > 5 and "confidence" in evaluated.columns:
    col_a, col_b = st.columns(2)

    with col_a:
        st.subheader("Hit Rate by Confidence")
        conf_stats = evaluated.groupby("confidence").agg(
            predictions=("hit", "count"),
            hit_rate=("hit", "mean"),
        ).reset_index()
        conf_stats["hit_rate_pct"] = (conf_stats["hit_rate"] * 100).round(1)
        fig_conf = px.bar(conf_stats, x="confidence", y="hit_rate_pct",
                           color="confidence",
                           color_discrete_map={"High": "#15803d", "Medium": "#b45309", "Low": "#6b7280"},
                           labels={"hit_rate_pct": "Hit Rate (%)", "confidence": "Confidence"},
                           text="hit_rate_pct")
        fig_conf.update_traces(texttemplate="%{text}%", textposition="outside")
        fig_conf.update_layout(template="plotly_white", showlegend=False, height=300)
        st.plotly_chart(fig_conf, use_container_width=True)

    with col_b:
        st.subheader("Score vs Actual Move")
        if "score" in evaluated.columns:
            fig_scatter = px.scatter(
                evaluated, x="score", y="actual_move_5d",
                color="hit",
                color_discrete_map={True: "#16a34a", False: "#dc2626"},
                labels={"score": "Prediction Score", "actual_move_5d": "Actual Move (%)"},
                hover_data=["ticker", "date", "direction"],
            )
            fig_scatter.add_hline(y=5, line_dash="dot", line_color="#16a34a",
                                   annotation_text="+5% target")
            fig_scatter.add_hline(y=-5, line_dash="dot", line_color="#dc2626",
                                   annotation_text="-5% target")
            fig_scatter.update_layout(template="plotly_white", height=300)
            st.plotly_chart(fig_scatter, use_container_width=True)

st.divider()

# ── Direction accuracy ─────────────────────────────────────────────────────────
if len(evaluated) > 5 and "direction" in evaluated.columns:
    st.subheader("Direction Accuracy")
    evaluated["direction_correct"] = (
        ((evaluated["direction"] == "bullish") & (evaluated["actual_move_5d"] > 0)) |
        ((evaluated["direction"] == "bearish") & (evaluated["actual_move_5d"] < 0))
    )
    dir_acc = evaluated[evaluated["direction"] != "mixed"]["direction_correct"].mean()
    st.metric("Direction accuracy (excl. mixed)", f"{dir_acc*100:.1f}%")

st.divider()

# ── Full prediction log ────────────────────────────────────────────────────────
st.subheader("Full Prediction Log")
show_cols = [c for c in ["date", "ticker", "score", "direction", "confidence", "duration",
                          "signals_triggered", "actual_move_5d"]
             if c in filtered.columns]
display = filtered[show_cols].copy()
display["date"] = display["date"].dt.strftime("%Y-%m-%d")

def style_actual(val):
    if pd.isna(val):
        return ""
    if abs(val) >= 5:
        return "color: #16a34a; font-weight: bold" if val > 0 else "color: #dc2626; font-weight: bold"
    return "color: #6b7280"

styled = display.style.map(style_actual, subset=["actual_move_5d"]) if "actual_move_5d" in display.columns else display.style
st.dataframe(styled, use_container_width=True, height=400, hide_index=True)

st.download_button(
    label="Download CSV",
    data=filtered.to_csv(index=False),
    file_name="market_predictions.csv",
    mime="text/csv",
)
