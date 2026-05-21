"""
Track Record — full performance analytics.

Sections:
  1. KPI bar      — Win Rate, Profit Factor, Expected Value, Max Drawdown, Total P&L
  2. Equity curve — cumulative P&L over time (main visual)
  3. Monthly P&L  — calendar heatmap
  4. Signal attribution — which signals actually predict wins
  5. Win/Loss distribution — histogram of trade returns
  6. Score calibration — does a higher score = better outcome?
  7. Best / Worst trades
  8. Full prediction log (table + export)
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from ui_style import inject_css, section_header, live_badge
from config import MOVE_TARGET_PCT

st.set_page_config(page_title="Track Record", page_icon="📋", layout="wide")
inject_css()

st.markdown(
    f'<h2 style="color:#e8f4ff;font-weight:700;">Track Record{live_badge()}</h2>'
    f'<p style="color:#5a8a9f;font-size:13px;margin-top:-8px;">'
    f'Performance analytics · Signal attribution · Equity curve</p>',
    unsafe_allow_html=True
)

# ── Load data ─────────────────────────────────────────────────────────────────
try:
    from db import load_predictions, db_available
    if not db_available():
        st.markdown(
            '<div style="color:#f59e0b;padding:20px;background:#161616;border:1px solid #1e1e1e;border-radius:6px;">'
            '⚠ Supabase not configured. Add SUPABASE_URL and SUPABASE_KEY to .env</div>',
            unsafe_allow_html=True)
        st.stop()
    rows = load_predictions()
except Exception as e:
    st.error(f"Could not load predictions: {e}")
    st.stop()

if not rows:
    st.markdown(
        '<div style="color:#333;text-align:center;padding:80px 0;">'
        'No predictions yet — run a scan first</div>',
        unsafe_allow_html=True)
    st.stop()

log = pd.DataFrame(rows)
log["date"] = pd.to_datetime(log["date"])
log = log.sort_values("date", ascending=False)

# ── Sidebar filters ───────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown(
        '<div style="color:#5a8a9f;font-size:11px;letter-spacing:1px;'
        'text-transform:uppercase;margin-bottom:12px;">Filters</div>',
        unsafe_allow_html=True
    )
    min_date  = log["date"].min().date()
    max_date  = log["date"].max().date()
    date_range = st.date_input(
        "Date range", value=(min_date, max_date),
        min_value=min_date, max_value=max_date
    )
    dir_filter  = st.multiselect("Direction", ["bullish","bearish","mixed"],
                                  default=["bullish","bearish","mixed"])
    conf_filter = st.multiselect("Confidence", ["High","Medium","Low"],
                                  default=["High","Medium","Low"])

filtered = log.copy()
if len(date_range) == 2:
    filtered = filtered[
        (filtered["date"].dt.date >= date_range[0]) &
        (filtered["date"].dt.date <= date_range[1])
    ]
if dir_filter:
    filtered = filtered[filtered["direction"].isin(dir_filter)]
if conf_filter and "confidence" in filtered.columns:
    filtered = filtered[filtered["confidence"].isin(conf_filter)]

# ── Evaluated trades (have actual outcome) ───────────────────────────────────
evaluated = pd.DataFrame()
if "actual_move_5d" in filtered.columns:
    evaluated = filtered[filtered["actual_move_5d"].notna()].copy()

if not evaluated.empty:
    # P&L per trade (directionally aware)
    def _compute_pl(row):
        move      = row.get("actual_move_5d", 0)
        dollar    = row.get("dollar_amount", 1000)
        if pd.isna(dollar) or dollar == 0:
            dollar = 1000
        direction = row.get("direction", "bullish")
        if direction == "bullish":
            return dollar * (move / 100)
        elif direction == "bearish":
            return dollar * (-move / 100)
        return 0.0

    evaluated["trade_pl"] = evaluated.apply(_compute_pl, axis=1)
    _dollar_col = evaluated["dollar_amount"].fillna(1000).replace(0, 1000) if "dollar_amount" in evaluated.columns else pd.Series(1000, index=evaluated.index)
    evaluated["trade_return"] = evaluated["trade_pl"] / _dollar_col

    # Directional hit (win = P&L > 0)
    evaluated["win"] = evaluated["trade_pl"] > 0

    # Sort chronologically for equity curve
    evaluated_chron = evaluated.sort_values("date")
    evaluated_chron["cumulative_pl"] = evaluated_chron["trade_pl"].cumsum()


# ══════════════════════════════════════════════════════════════════════════════
# KPI BAR
# ══════════════════════════════════════════════════════════════════════════════
section_header("PERFORMANCE SUMMARY")

k_cols = st.columns(7)
total_preds = len(filtered)
total_eval  = len(evaluated)

k_cols[0].metric("Total Predictions", total_preds)
k_cols[1].metric("Evaluated", total_eval)

if not evaluated.empty and total_eval > 0:
    wins      = evaluated["win"].sum()
    losses    = total_eval - wins
    win_rate  = wins / total_eval

    gross_profit = evaluated[evaluated["trade_pl"] > 0]["trade_pl"].sum()
    gross_loss   = abs(evaluated[evaluated["trade_pl"] <= 0]["trade_pl"].sum())
    profit_factor = gross_profit / max(gross_loss, 1)

    avg_win  = evaluated[evaluated["win"]]["trade_pl"].mean()  if wins  > 0 else 0
    avg_loss = evaluated[~evaluated["win"]]["trade_pl"].mean() if losses > 0 else 0

    ev = win_rate * avg_win + (1 - win_rate) * avg_loss  # expected value per trade

    total_pl = evaluated["trade_pl"].sum()

    # Max drawdown from equity curve
    cum_pl   = evaluated_chron["cumulative_pl"].values
    peak     = np.maximum.accumulate(cum_pl)
    drawdown = cum_pl - peak
    max_dd   = float(drawdown.min()) if len(drawdown) > 0 else 0.0

    k_cols[2].metric("Win Rate",      f"{win_rate:.1%}",
                     delta=f"{wins}W / {losses}L")
    k_cols[3].metric("Profit Factor", f"{profit_factor:.2f}",
                     delta="above 1 = profitable" if profit_factor > 1 else "below 1 = losing",
                     delta_color="normal" if profit_factor > 1 else "inverse")
    k_cols[4].metric("Expected Value", f"${ev:+,.0f}/trade")
    k_cols[5].metric("Max Drawdown",   f"${max_dd:,.0f}",
                     delta_color="inverse")
    k_cols[6].metric("Total P&L",      f"${total_pl:+,.0f}",
                     delta_color="normal" if total_pl >= 0 else "inverse")
else:
    k_cols[2].metric("Win Rate",       "—")
    k_cols[3].metric("Profit Factor",  "—")
    k_cols[4].metric("Expected Value", "—")
    k_cols[5].metric("Max Drawdown",   "—")
    k_cols[6].metric("Total P&L",      "—")


# ══════════════════════════════════════════════════════════════════════════════
# EQUITY CURVE
# ══════════════════════════════════════════════════════════════════════════════
if not evaluated.empty and len(evaluated) >= 3:
    st.divider()
    section_header("EQUITY CURVE — Cumulative P&L")

    eq_df = evaluated_chron[["date","cumulative_pl","win","ticker","score","direction"]].copy()
    eq_df["date"] = eq_df["date"].dt.strftime("%Y-%m-%d")

    fig_eq = go.Figure()

    # Zero line
    fig_eq.add_hline(y=0, line_dash="dot", line_color="#333", line_width=1)

    # Shade profit / loss zones
    fig_eq.add_traces([
        go.Scatter(
            x=eq_df["date"], y=eq_df["cumulative_pl"].clip(lower=0),
            fill="tozeroy", fillcolor="rgba(0,255,136,0.06)",
            line=dict(width=0), showlegend=False, hoverinfo="skip",
        ),
        go.Scatter(
            x=eq_df["date"], y=eq_df["cumulative_pl"].clip(upper=0),
            fill="tozeroy", fillcolor="rgba(239,68,68,0.08)",
            line=dict(width=0), showlegend=False, hoverinfo="skip",
        ),
    ])

    # Main line
    color_vals = ["#00ff88" if w else "#ef4444" for w in eq_df["win"]]
    fig_eq.add_trace(go.Scatter(
        x=eq_df["date"], y=eq_df["cumulative_pl"],
        mode="lines+markers",
        line=dict(color="#00bfff", width=2.5),
        marker=dict(color=color_vals, size=6, line=dict(width=0)),
        hovertemplate=(
            "<b>%{customdata[0]}</b><br>"
            "Cumulative P&L: $%{y:,.0f}<br>"
            "Score: %{customdata[1]:.0f} · %{customdata[2]}<br>"
            "<extra></extra>"
        ),
        customdata=list(zip(eq_df["ticker"], eq_df["score"], eq_df["direction"])),
        name="Equity",
    ))

    fig_eq.update_layout(
        template="plotly_dark",
        paper_bgcolor="#0a0f1a",
        plot_bgcolor="#0a0f1a",
        height=280,
        margin=dict(l=0, r=0, t=10, b=0),
        yaxis=dict(
            gridcolor="#0d1520", tickprefix="$",
            tickformat=",.0f", title="Cumulative P&L",
            titlefont=dict(color="#5a8a9f"),
        ),
        xaxis=dict(gridcolor="#0d1520", title=""),
        hovermode="x unified",
        showlegend=False,
    )
    st.plotly_chart(fig_eq, use_container_width=True)


# ══════════════════════════════════════════════════════════════════════════════
# MONTHLY P&L HEATMAP + SIGNAL ATTRIBUTION
# ══════════════════════════════════════════════════════════════════════════════
if not evaluated.empty and len(evaluated) >= 5:
    st.divider()
    row1_a, row1_b = st.columns([1, 1])

    # ── Monthly P&L calendar ──────────────────────────────────────────────────
    with row1_a:
        section_header("MONTHLY P&L")
        monthly = evaluated_chron.copy()
        monthly["year"]  = monthly["date"].dt.year
        monthly["month"] = monthly["date"].dt.month
        monthly_pl = monthly.groupby(["year","month"])["trade_pl"].sum().reset_index()
        monthly_pl["month_name"] = monthly_pl["month"].apply(
            lambda m: ["Jan","Feb","Mar","Apr","May","Jun",
                       "Jul","Aug","Sep","Oct","Nov","Dec"][m-1]
        )

        pivot = monthly_pl.pivot(index="year", columns="month_name", values="trade_pl")
        month_order = ["Jan","Feb","Mar","Apr","May","Jun",
                       "Jul","Aug","Sep","Oct","Nov","Dec"]
        existing_months = [m for m in month_order if m in pivot.columns]
        pivot = pivot[existing_months]

        fig_cal = go.Figure(data=go.Heatmap(
            z=pivot.values,
            x=pivot.columns.tolist(),
            y=[str(y) for y in pivot.index.tolist()],
            colorscale=[[0,"#6b0f1a"],[0.5,"#1a1a2e"],[1,"#005a2e"]],
            zmid=0,
            text=[[f"${v:+,.0f}" if not np.isnan(v) else ""
                   for v in row]
                  for row in pivot.values],
            texttemplate="%{text}",
            textfont=dict(size=11, color="#e8f4ff"),
            hovertemplate="<b>%{y} %{x}</b><br>P&L: $%{z:+,.0f}<extra></extra>",
            showscale=False,
        ))
        fig_cal.update_layout(
            template="plotly_dark",
            paper_bgcolor="#0a0f1a",
            plot_bgcolor="#0a0f1a",
            height=200,
            margin=dict(l=0, r=0, t=10, b=0),
            xaxis=dict(side="top"),
        )
        st.plotly_chart(fig_cal, use_container_width=True)

    # ── Signal attribution ────────────────────────────────────────────────────
    with row1_b:
        section_header("SIGNAL WIN RATE")

        sig_rows = []
        for _, row in evaluated.iterrows():
            signals = row.get("signals_triggered", []) or []
            if isinstance(signals, str):
                try:
                    import json
                    signals = json.loads(signals)
                except Exception:
                    signals = [signals] if signals else []
            is_win = bool(row.get("win", False))
            for sig in signals:
                # Extract signal name (first word or up to the parenthesis)
                sig_name = sig.split(" (")[0].split(" +")[0].strip()
                sig_rows.append({"signal": sig_name, "win": is_win})

        if sig_rows:
            sig_df = pd.DataFrame(sig_rows)
            sig_stats = (sig_df.groupby("signal")
                         .agg(trades=("win","count"), wins=("win","sum"))
                         .reset_index())
            sig_stats["win_rate"] = sig_stats["wins"] / sig_stats["trades"] * 100
            sig_stats = sig_stats[sig_stats["trades"] >= 3].sort_values("win_rate", ascending=True)

            if not sig_stats.empty:
                colors = ["#00ff88" if w >= 60 else "#f59e0b" if w >= 45 else "#ef4444"
                          for w in sig_stats["win_rate"]]
                fig_sig = go.Figure(go.Bar(
                    x=sig_stats["win_rate"],
                    y=sig_stats["signal"],
                    orientation="h",
                    marker_color=colors,
                    text=[f"{w:.0f}% ({n})" for w, n in zip(sig_stats["win_rate"], sig_stats["trades"])],
                    textposition="outside",
                    textfont=dict(color="#8ab8d4", size=11),
                    hovertemplate="<b>%{y}</b><br>Win Rate: %{x:.1f}%<extra></extra>",
                ))
                fig_sig.add_vline(x=50, line_dash="dot", line_color="#333")
                fig_sig.update_layout(
                    template="plotly_dark",
                    paper_bgcolor="#0a0f1a",
                    plot_bgcolor="#0a0f1a",
                    height=220,
                    margin=dict(l=0, r=60, t=10, b=0),
                    xaxis=dict(gridcolor="#0d1520", range=[0, 110], title="Win Rate (%)"),
                    yaxis=dict(gridcolor="#0d1520", title=""),
                    showlegend=False,
                )
                st.plotly_chart(fig_sig, use_container_width=True)
        else:
            st.markdown('<div style="color:#333;padding:20px;">Not enough data yet</div>',
                        unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# WIN/LOSS DISTRIBUTION + SCORE CALIBRATION
# ══════════════════════════════════════════════════════════════════════════════
if not evaluated.empty and len(evaluated) >= 8:
    st.divider()
    row2_a, row2_b = st.columns(2)

    with row2_a:
        section_header("RETURN DISTRIBUTION")
        _d = evaluated["dollar_amount"].fillna(1000).replace(0, 1000) if "dollar_amount" in evaluated.columns else pd.Series(1000, index=evaluated.index)
        returns_pct = (evaluated["trade_pl"] / _d * 100).round(1)
        fig_hist = go.Figure()
        fig_hist.add_trace(go.Histogram(
            x=returns_pct[returns_pct >= 0],
            nbinsx=15,
            marker_color="#00ff88",
            opacity=0.7,
            name="Win",
            hovertemplate="Return: %{x:.1f}%<br>Count: %{y}<extra></extra>",
        ))
        fig_hist.add_trace(go.Histogram(
            x=returns_pct[returns_pct < 0],
            nbinsx=15,
            marker_color="#ef4444",
            opacity=0.7,
            name="Loss",
            hovertemplate="Return: %{x:.1f}%<br>Count: %{y}<extra></extra>",
        ))
        fig_hist.add_vline(x=0, line_dash="dot", line_color="#555")
        fig_hist.update_layout(
            template="plotly_dark",
            paper_bgcolor="#0a0f1a",
            plot_bgcolor="#0a0f1a",
            height=240,
            barmode="overlay",
            margin=dict(l=0, r=0, t=10, b=0),
            xaxis=dict(gridcolor="#0d1520", title="Trade Return (%)"),
            yaxis=dict(gridcolor="#0d1520", title="Count"),
            legend=dict(x=0.8, y=0.95, font=dict(color="#8ab8d4")),
        )
        st.plotly_chart(fig_hist, use_container_width=True)

    with row2_b:
        section_header("SCORE CALIBRATION")
        if "score" in evaluated.columns:
            fig_cal2 = go.Figure()
            # Add avg return by score bucket (10-point buckets)
            eval_copy = evaluated.copy()
            eval_copy["score_bucket"] = (eval_copy["score"] // 10 * 10).astype(int)
            bucket_stats = eval_copy.groupby("score_bucket").agg(
                avg_return=("trade_pl", "mean"),
                count=("trade_pl", "count"),
                win_rate=("win", "mean"),
            ).reset_index()

            bar_colors = ["#00ff88" if r > 0 else "#ef4444" for r in bucket_stats["avg_return"]]
            fig_cal2.add_trace(go.Bar(
                x=bucket_stats["score_bucket"].astype(str) + "s",
                y=bucket_stats["avg_return"],
                marker_color=bar_colors,
                text=[f"${v:+,.0f}<br>{wr:.0%}" for v, wr in zip(bucket_stats["avg_return"], bucket_stats["win_rate"])],
                textposition="outside",
                textfont=dict(color="#8ab8d4", size=10),
                hovertemplate="Score: %{x}<br>Avg P&L: $%{y:,.0f}<extra></extra>",
            ))
            fig_cal2.add_hline(y=0, line_dash="dot", line_color="#333")
            fig_cal2.update_layout(
                template="plotly_dark",
                paper_bgcolor="#0a0f1a",
                plot_bgcolor="#0a0f1a",
                height=240,
                margin=dict(l=0, r=0, t=10, b=0),
                xaxis=dict(gridcolor="#0d1520", title="Score Range", categoryorder="array",
                           categoryarray=["50s","60s","70s","80s","90s"]),
                yaxis=dict(gridcolor="#0d1520", title="Avg P&L ($)", tickprefix="$"),
                showlegend=False,
            )
            st.plotly_chart(fig_cal2, use_container_width=True)


# ══════════════════════════════════════════════════════════════════════════════
# BEST / WORST TRADES
# ══════════════════════════════════════════════════════════════════════════════
if not evaluated.empty and len(evaluated) >= 5:
    st.divider()
    bw_a, bw_b = st.columns(2)

    def _trade_table(df: pd.DataFrame, label: str, color: str):
        rows_html = ""
        for _, row in df.iterrows():
            ticker = row.get("ticker","")
            date_s = str(row.get("date",""))[:10]
            dir_   = row.get("direction","")
            score_ = row.get("score",0)
            pl     = row.get("trade_pl", 0)
            move   = row.get("actual_move_5d", 0)
            arrow  = "▲" if pl >= 0 else "▼"
            rows_html += (
                f'<tr style="border-bottom:1px solid #0d1520;">'
                f'<td style="padding:7px 10px;font-family:JetBrains Mono,monospace;'
                f'font-weight:700;color:#e8f4ff;">{ticker}</td>'
                f'<td style="padding:7px 10px;color:#5a8a9f;font-size:12px;">{date_s}</td>'
                f'<td style="padding:7px 10px;font-family:JetBrains Mono,monospace;'
                f'color:{color};font-weight:700;">{arrow} ${abs(pl):,.0f}</td>'
                f'<td style="padding:7px 10px;color:#8ab8d4;font-size:12px;">{move:+.1f}%</td>'
                f'<td style="padding:7px 10px;color:#5a8a9f;font-size:12px;">{score_:.0f}</td>'
                f'</tr>'
            )
        return (
            f'<div style="border:1px solid #0d1520;border-radius:6px;overflow:hidden;">'
            f'<table width="100%" cellpadding="0" cellspacing="0" style="border-collapse:collapse;">'
            f'<thead><tr style="background:#0a0f1a;">'
            f'<th style="padding:8px 10px;text-align:left;color:#5a8a9f;font-size:10px;letter-spacing:1px;text-transform:uppercase;">Ticker</th>'
            f'<th style="padding:8px 10px;text-align:left;color:#5a8a9f;font-size:10px;letter-spacing:1px;text-transform:uppercase;">Date</th>'
            f'<th style="padding:8px 10px;text-align:left;color:#5a8a9f;font-size:10px;letter-spacing:1px;text-transform:uppercase;">P&L</th>'
            f'<th style="padding:8px 10px;text-align:left;color:#5a8a9f;font-size:10px;letter-spacing:1px;text-transform:uppercase;">Move</th>'
            f'<th style="padding:8px 10px;text-align:left;color:#5a8a9f;font-size:10px;letter-spacing:1px;text-transform:uppercase;">Score</th>'
            f'</tr></thead>'
            f'<tbody>{rows_html}</tbody>'
            f'</table></div>'
        )

    best_trades  = evaluated.nlargest(5, "trade_pl")[["ticker","date","direction","score","trade_pl","actual_move_5d"]]
    worst_trades = evaluated.nsmallest(5, "trade_pl")[["ticker","date","direction","score","trade_pl","actual_move_5d"]]

    with bw_a:
        section_header("🏆 BEST TRADES")
        st.markdown(_trade_table(best_trades, "Best Trades", "#00ff88"), unsafe_allow_html=True)

    with bw_b:
        section_header("💀 WORST TRADES")
        st.markdown(_trade_table(worst_trades, "Worst Trades", "#ef4444"), unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# FULL PREDICTION LOG
# ══════════════════════════════════════════════════════════════════════════════
st.divider()
section_header("PREDICTION LOG")

show_cols = [c for c in ["date","ticker","score","direction","confidence",
                          "duration","actual_move_5d","trade_pl"] if c in filtered.columns]
display = filtered[show_cols].copy()
display["date"] = display["date"].dt.strftime("%Y-%m-%d")

rows_html = ""
for _, row in display.iterrows():
    move = row.get("actual_move_5d", None)
    pl   = row.get("trade_pl", None)

    if move is None or (hasattr(move, '__class__') and pd.isna(move)):
        move_str = '<span style="color:#333;">Pending</span>'
    else:
        hit    = abs(move) >= MOVE_TARGET_PCT * 100
        color  = "#00ff88" if hit else "#5a8a9f"
        arrow  = "▲" if move > 0 else "▼" if move < 0 else "→"
        move_str = f'<span style="color:{color};font-family:JetBrains Mono,monospace;">{arrow} {abs(move):.1f}%</span>'

    if pl is not None and not pd.isna(pl):
        pl_color = "#00ff88" if pl >= 0 else "#ef4444"
        pl_str = f'<span style="color:{pl_color};font-family:JetBrains Mono,monospace;">${pl:+,.0f}</span>'
    else:
        pl_str = '<span style="color:#333;">—</span>'

    dir_ = row.get("direction","")
    dir_color = {"bullish":"#00ff88","bearish":"#ef4444"}.get(dir_,"#5a8a9f")
    score_ = row.get("score", 0)
    score_color = "#00ff88" if score_ >= 70 else "#f59e0b" if score_ >= 50 else "#5a8a9f"
    conf_ = row.get("confidence","")
    conf_color = {"High":"#00ff88","Medium":"#f59e0b","Low":"#5a8a9f"}.get(conf_,"#5a8a9f")

    rows_html += (
        f'<tr style="border-bottom:1px solid #0d1520;">'
        f'<td style="padding:8px 12px;color:#5a8a9f;font-size:12px;">{row.get("date","")}</td>'
        f'<td style="padding:8px 12px;font-family:JetBrains Mono,monospace;font-weight:700;color:#e8f4ff;">{row.get("ticker","")}</td>'
        f'<td style="padding:8px 12px;font-family:JetBrains Mono,monospace;color:{score_color};">{score_:.0f}</td>'
        f'<td style="padding:8px 12px;color:{dir_color};font-weight:600;font-size:12px;">{dir_.upper()}</td>'
        f'<td style="padding:8px 12px;color:{conf_color};font-size:12px;">{conf_}</td>'
        f'<td style="padding:8px 12px;color:#5a8a9f;font-size:12px;">{row.get("duration","")}</td>'
        f'<td style="padding:8px 12px;">{move_str}</td>'
        f'<td style="padding:8px 12px;">{pl_str}</td>'
        f'</tr>'
    )

headers = ["Date","Ticker","Score","Direction","Confidence","Window","Actual Move","P&L"]
header_html = "".join(
    f'<th style="padding:10px 12px;text-align:left;color:#5a8a9f;font-size:11px;'
    f'letter-spacing:1px;text-transform:uppercase;">{h}</th>' for h in headers
)

st.markdown(f"""
<div style="overflow-y:auto;max-height:500px;border:1px solid #0d1520;border-radius:6px;">
<table width="100%" cellpadding="0" cellspacing="0" style="border-collapse:collapse;background:#060d17;">
  <thead style="position:sticky;top:0;z-index:1;">
    <tr style="background:#0a0f1a;">{header_html}</tr>
  </thead>
  <tbody>{rows_html}</tbody>
</table>
</div>
""", unsafe_allow_html=True)

st.markdown("<div style='margin-top:12px;'></div>", unsafe_allow_html=True)

# Add trade_pl to export if computed
export_df = filtered.copy()
if not evaluated.empty and "trade_pl" in evaluated.columns:
    export_df = export_df.merge(
        evaluated[["ticker","date","trade_pl","win"]],
        on=["ticker","date"], how="left"
    )

st.download_button(
    "⬇ Export CSV",
    export_df.to_csv(index=False),
    file_name="track_record.csv",
    mime="text/csv",
)
