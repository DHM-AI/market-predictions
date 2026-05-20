import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
from ui_style import inject_css, live_badge, signal_tags

st.set_page_config(page_title="AI Market Scanner", page_icon="📡", layout="wide")
inject_css()

st.markdown("""
<style>
.scanner-title{font-size:20px;font-weight:700;color:#e8e8e8;display:flex;align-items:center;gap:10px;}
.agent-main-card{background:#111;border:1px solid #1e1e1e;border-radius:8px;padding:14px 16px;margin-bottom:10px;display:flex;justify-content:space-between;align-items:center;}
.agent-main-name{font-size:14px;font-weight:600;color:#e8e8e8;}
.agent-main-sub{font-size:11px;color:#555;margin-top:3px;}
.agent-main-val{font-family:'JetBrains Mono',monospace;font-size:26px;font-weight:700;color:#00ff88;}
.pipeline-wrap{background:#111;border:1px solid #1e1e1e;border-radius:8px;overflow:hidden;margin-bottom:10px;}
.pipeline-label{font-size:11px;color:#444;letter-spacing:1.5px;text-transform:uppercase;padding:10px 16px 8px;border-bottom:1px solid #1a1a1a;}
.pip-step{display:flex;align-items:center;padding:9px 16px;border-bottom:1px solid #0f0f0f;gap:12px;}
.pip-step:last-child{border-bottom:none;}
.pip-dot-on{width:9px;height:9px;border-radius:50%;background:#00ff88;box-shadow:0 0 5px #00ff8888;flex-shrink:0;}
.pip-dot-pend{width:9px;height:9px;border-radius:50%;background:#2a2a2a;border:1px solid #3a3a3a;flex-shrink:0;}
.pip-step-name{font-size:13px;color:#e8e8e8;font-weight:500;flex:0 0 90px;}
.pip-step-sub{font-size:11px;color:#555;flex:1;}
.pip-bar-wrap{width:80px;height:4px;background:#1a1a1a;border-radius:2px;flex-shrink:0;}
.pip-bar-fill{height:4px;background:#00ff88;border-radius:2px;}
.pip-step-num{font-family:'JetBrains Mono',monospace;font-weight:600;font-size:15px;min-width:40px;text-align:right;flex-shrink:0;}
.qual-bar{display:flex;justify-content:space-between;align-items:center;background:#0a1f14;border:1px solid #00ff8844;border-radius:8px;padding:14px 18px;margin-top:6px;}
.qual-label{color:#00ff88;font-size:12px;font-weight:500;}
.qual-count{font-family:'JetBrains Mono',monospace;font-size:28px;font-weight:700;color:#00ff88;}
.ticker-wrap{background:#111;border:1px solid #1e1e1e;border-radius:8px;overflow:hidden;}
.ticker-header{font-size:11px;color:#444;letter-spacing:1.5px;text-transform:uppercase;padding:10px 14px 8px;border-bottom:1px solid #1a1a1a;}
.ticker-row{display:flex;justify-content:space-between;align-items:center;padding:7px 14px;border-bottom:1px solid #0f0f0f;font-size:12px;}
.ticker-row:last-child{border-bottom:none;}
.t-sym{font-weight:700;color:#e8e8e8;width:58px;font-family:'JetBrains Mono',monospace;}
.t-price{color:#666;font-family:'JetBrains Mono',monospace;flex:1;text-align:right;padding-right:10px;}
.t-up{color:#00ff88;font-family:'JetBrains Mono',monospace;min-width:52px;text-align:right;}
.t-dn{color:#ff4444;font-family:'JetBrains Mono',monospace;min-width:52px;text-align:right;}
</style>
""", unsafe_allow_html=True)

for k, v in [("pipeline_counts",{}),("last_picks",None),("ticker_tape",[]),("scan_time","")]:
    if k not in st.session_state: st.session_state[k] = v

col_title, col_btn = st.columns([3,1])
with col_title:
    st.markdown(f'<div class="scanner-title">AI Market Scanner {live_badge()}</div><div style="color:#444;font-size:12px;margin-top:4px;">S&P 500 + Futures · 5-Agent Pipeline · 5-10% Move Detection</div>', unsafe_allow_html=True)
with col_btn:
    run_clicked = st.button("▶  Run Scan", type="primary", use_container_width=True)

st.divider()
left_col, right_col = st.columns([1,2], gap="medium")

with left_col:
    tape_ph = st.empty()
    def render_tape(data):
        if not data:
            tape_ph.markdown('<div class="ticker-wrap"><div class="ticker-header">ACTIVE UNIVERSE</div><div style="color:#555;padding:40px 14px;font-size:12px;text-align:center;line-height:2;">📡 Press <strong style="color:#00ff88;">Run Scan</strong><br>to fetch S&P 500 + Futures</div></div>', unsafe_allow_html=True)
            return
        rows = ""
        for t in data[:40]:
            chg=t.get("chg_pct",0); cls="t-up" if chg>=0 else "t-dn"; sign="+" if chg>=0 else ""
            px=f'${t["price"]:,.2f}' if t.get("price") else "—"
            rows+=f'<div class="ticker-row"><span class="t-sym">{t["ticker"]}</span><span class="t-price">{px}</span><span class="{cls}">{sign}{chg:.1f}%</span></div>'
        tape_ph.markdown(f'<div class="ticker-wrap"><div class="ticker-header">ACTIVE UNIVERSE</div><div style="overflow-y:auto;max-height:560px;">{rows}</div></div>', unsafe_allow_html=True)
    render_tape(st.session_state["ticker_tape"])

with right_col:
    agent_ph=st.empty(); pipeline_ph=st.empty(); qual_ph=st.empty()

    def render_agent(name, sub, count, running=False):
        pulse="animation:blink 0.9s infinite;" if running else ""
        dot_color="#00ff88" if (running or count not in ("—","0","")) else "#444"
        val_color="#00ff88" if count not in ("—","") else "#444"
        agent_ph.markdown(f'<div class="agent-main-card"><div><div class="agent-main-name"><span style="display:inline-block;width:9px;height:9px;border-radius:50%;background:{dot_color};margin-right:9px;{pulse}"></span>{name}</div><div class="agent-main-sub" style="margin-left:18px;">{sub}</div></div><div class="agent-main-val" style="color:{val_color};">{count}</div></div>', unsafe_allow_html=True)

    def render_pipeline(counts, universe=509):
        steps=[("Scan","Fetch OHLCV · yfinance",counts.get("universe",universe),universe),("Research","Reddit · RSS · Alpha Vantage",counts.get("research"),universe),("Predict","XGBoost + blended sentiment",counts.get("scored"),universe),("Risk","Kelly Criterion · $50k bankroll",counts.get("risk"),universe),("Learn","Backfill actuals · post-mortem",counts.get("learn"),universe)]
        rows=""
        for name,sub,cnt,total in steps:
            done=cnt is not None; dot="pip-dot-on" if done else "pip-dot-pend"; nc="color:#00ff88" if done else "color:#444"
            cnt_str=str(cnt) if cnt is not None else "—"; bar_pct=int((cnt/total)*100) if (done and total) else 0
            rows+=f'<div class="pip-step"><div class="{dot}"></div><div class="pip-step-name">{name}</div><div class="pip-step-sub">{sub}</div><div class="pip-bar-wrap"><div class="pip-bar-fill" style="width:{bar_pct}%;"></div></div><div class="pip-step-num" style="{nc}">{cnt_str}</div></div>'
        pipeline_ph.markdown(f'<div class="pipeline-wrap"><div class="pipeline-label">Filter Pipeline</div>{rows}</div>', unsafe_allow_html=True)

    def render_qualified(n):
        if n>0:
            qual_ph.markdown(f'<div class="qual-bar"><div><div class="qual-label">Qualified Setups</div><div style="color:#00ff88;font-size:11px;margin-top:2px;">Score ≥ 50 · Move target 5%+</div></div><div class="qual-count">{n} <span style="font-size:14px;font-weight:400;">found</span></div></div>', unsafe_allow_html=True)
        else:
            qual_ph.markdown('<div style="border:1px solid #1e1e1e;border-radius:8px;padding:14px 18px;display:flex;justify-content:space-between;align-items:center;margin-top:6px;"><div style="color:#555;font-size:12px;">Qualified Setups · Score ≥ 50</div><div style="color:#444;font-family:JetBrains Mono,monospace;font-size:22px;">—</div></div>', unsafe_allow_html=True)

    picks_df=st.session_state["last_picks"]; counts=st.session_state["pipeline_counts"]; scan_time=st.session_state["scan_time"]
    n_picks=len(picks_df) if picks_df is not None and not picks_df.empty else 0
    render_agent("Market Scan Agent", f"Last scan: {scan_time}" if scan_time else "Ready — press ▶ Run Scan to start", str(n_picks) if n_picks else "—")
    render_pipeline(counts); render_qualified(n_picks)

if run_clicked:
    from data.universe import get_universe
    from data.fetcher import get_ohlcv_batch, get_earnings_days
    from data.research import research_universe
    from signals.sentiment import get_sentiment_with_velocity
    from signals.kelly import annotate_picks
    from model.predictor import predict_universe
    import db

    tickers=get_universe(); N=len(tickers)
    render_agent("Market Scan Agent", f"Fetching data for {N} tickers...", str(N), running=True)
    render_pipeline({}); render_qualified(0)
    with st.spinner(""):
        ohlcv_map=get_ohlcv_batch(tickers, period="1y", chunk_size=50)
    tape=[{"ticker":t,"price":float(df["Close"].iloc[-1]),"chg_pct":(float(df["Close"].iloc[-1])-float(df["Close"].iloc[-2]))/float(df["Close"].iloc[-2])*100} for t,df in ohlcv_map.items() if not df.empty and len(df)>=2]
    tape.sort(key=lambda x:abs(x["chg_pct"]),reverse=True)
    st.session_state["ticker_tape"]=tape; render_tape(tape)

    render_agent("Research Agent","Running Reddit · RSS · news sentiment...",str(N),running=True); render_pipeline({"universe":N})
    with st.spinner(""):
        blended=research_universe(tickers)
        sentiment_map={t:{**blended.get(t,{}),"score":round(get_sentiment_with_velocity(t).get("score",0)*0.4+blended.get(t,{}).get("score",0)*0.6,4),"velocity":get_sentiment_with_velocity(t).get("velocity",0),"spike":abs(get_sentiment_with_velocity(t).get("velocity",0))>=0.3 or blended.get(t,{}).get("score",0)>0.4} for t in tickers}

    render_agent("Predict Agent","Scoring with XGBoost + sentiment...",str(N),running=True); render_pipeline({"universe":N,"research":N})
    with st.spinner(""):
        earnings_map={t:get_earnings_days(t) for t in tickers[:100]}
        picks_df=predict_universe(tickers,ohlcv_map,sentiment_map,earnings_map)
    scored=len(picks_df) if picks_df is not None and not picks_df.empty else 0

    render_agent("Risk Agent","Calculating Kelly Criterion sizes...",str(scored),running=True); render_pipeline({"universe":N,"research":N,"scored":scored})
    if picks_df is not None and not picks_df.empty: picks_df=annotate_picks(picks_df)

    render_agent("Learn Agent","Persisting to Supabase...",str(scored),running=True); render_pipeline({"universe":N,"research":N,"scored":scored,"risk":scored})
    with st.spinner(""):
        if picks_df is not None and not picks_df.empty and db.db_available():
            rows=picks_df.copy(); rows["date"]=datetime.today().strftime("%Y-%m-%d"); rows["actual_move_5d"]=None
            db.append_predictions(rows.to_dict(orient="records"))

    scan_time=datetime.now().strftime("%H:%M")
    st.session_state.update({"last_picks":picks_df,"scan_time":scan_time,"pipeline_counts":{"universe":N,"research":N,"scored":scored,"risk":scored,"learn":scored}})
    render_agent("Market Scan Agent",f"Completed at {scan_time}",str(scored)); render_pipeline(st.session_state["pipeline_counts"]); render_qualified(scored)

if picks_df is None:
    try:
        from db import load_predictions_for_date,db_available
        if db_available():
            rows=load_predictions_for_date(datetime.today().strftime("%Y-%m-%d"))
            if rows: picks_df=pd.DataFrame(rows); render_qualified(len(picks_df))
    except Exception: pass

if picks_df is not None and not picks_df.empty:
    st.divider()
    st.markdown(f'<div style="font-size:13px;font-weight:600;color:#e8e8e8;margin-bottom:12px;">{len(picks_df)} setups flagged</div>', unsafe_allow_html=True)
    rows_html=""
    for _,row in picks_df.iterrows():
        ticker=row.get("ticker",""); score=row.get("score",0); direct=row.get("direction","mixed"); dur=row.get("duration","—"); conf=row.get("confidence","—"); rsi=row.get("rsi","—"); vol=row.get("volume_ratio","—"); kelly=row.get("dollar_amount",0); sigs=row.get("signals_triggered",[])
        if isinstance(sigs,str): sigs=[s.strip() for s in sigs.split(";") if s.strip()]
        sc="#00ff88" if score>=70 else "#f59e0b" if score>=50 else "#888"; dc="#00ff88" if direct=="bullish" else "#ff4444" if direct=="bearish" else "#f59e0b"; da="▲" if direct=="bullish" else "▼" if direct=="bearish" else "◆"; cc={"High":"#00ff88","Medium":"#f59e0b","Low":"#555"}.get(conf,"#555")
        ks=f'${kelly:,.0f}' if kelly else "—"; rs=f"{rsi:.1f}" if isinstance(rsi,float) else str(rsi); vs=f"{vol:.1f}x" if isinstance(vol,float) else str(vol)
        sh="".join(f'<span style="display:inline-block;background:#0a1f14;border:1px solid #00ff8844;color:#00ff88;font-size:10px;padding:1px 7px;border-radius:3px;margin:1px;">{s}</span>' for s in sigs[:3])
        rows_html+=f'<tr><td style="padding:10px 12px;font-weight:700;color:#e8e8e8;font-size:14px;font-family:JetBrains Mono,monospace;">{ticker}</td><td style="padding:10px 12px;font-family:JetBrains Mono,monospace;font-weight:700;color:{sc};font-size:15px;">{score:.0f}</td><td style="padding:10px 12px;color:{dc};font-weight:600;font-size:13px;">{da} {direct.capitalize()}</td><td style="padding:10px 12px;color:#555;font-size:12px;">{dur}</td><td style="padding:10px 12px;color:{cc};font-size:12px;font-weight:600;">{conf}</td><td style="padding:10px 12px;font-family:JetBrains Mono,monospace;color:#888;font-size:12px;">{rs}</td><td style="padding:10px 12px;font-family:JetBrains Mono,monospace;color:#888;font-size:12px;">{vs}</td><td style="padding:10px 12px;font-family:JetBrains Mono,monospace;color:#00ff88;font-weight:700;font-size:13px;">{ks}</td><td style="padding:10px 12px;">{sh}</td></tr>'
    hdrs=["Ticker","Score","Signal","Window","Confidence","RSI","Vol","Kelly $","Triggers"]
    th="".join(f'<th style="padding:10px 12px;text-align:left;color:#333;font-size:11px;font-weight:500;border-bottom:1px solid #1a1a1a;">{h}</th>' for h in hdrs)
    st.markdown(f'<div style="border:1px solid #1e1e1e;border-radius:8px;overflow:hidden;background:#0d0d0d;"><table width="100%" cellpadding="0" cellspacing="0" style="border-collapse:collapse;"><thead><tr style="background:#111;">{th}</tr></thead><tbody>{rows_html}</tbody></table></div>', unsafe_allow_html=True)

    st.divider()
    selected=st.selectbox("",picks_df["ticker"].tolist(),label_visibility="collapsed")
    if selected:
        from data.fetcher import get_ohlcv
        from ta.volatility import BollingerBands as BB
        df=get_ohlcv(selected,period="6mo")
        if not df.empty:
            _bb=BB(df["Close"],window=20,window_dev=2)
            fig=go.Figure()
            fig.add_trace(go.Candlestick(x=df.index,open=df["Open"],high=df["High"],low=df["Low"],close=df["Close"],name=selected,increasing=dict(line=dict(color="#00ff88"),fillcolor="#00ff8820"),decreasing=dict(line=dict(color="#ff4444"),fillcolor="#ff444420")))
            try:
                fig.add_trace(go.Scatter(x=df.index,y=_bb.bollinger_hband(),line=dict(color="#00ff8844",width=1),showlegend=False))
                fig.add_trace(go.Scatter(x=df.index,y=_bb.bollinger_lband(),line=dict(color="#00ff8844",width=1),fill="tonexty",fillcolor="rgba(0,255,136,0.03)",showlegend=False))
            except Exception: pass
            fig.update_layout(xaxis_rangeslider_visible=False,height=360,paper_bgcolor="#0d0d0d",plot_bgcolor="#0d0d0d",xaxis=dict(gridcolor="#111",showgrid=True,tickfont=dict(color="#444",size=10)),yaxis=dict(gridcolor="#111",showgrid=True,tickfont=dict(color="#444",size=10)),margin=dict(l=0,r=0,t=10,b=0),title=dict(text=selected,font=dict(color="#e8e8e8",size=13),x=0.01))
            st.plotly_chart(fig,use_container_width=True)
            row=picks_df[picks_df["ticker"]==selected].iloc[0]; sigs=row.get("signals_triggered",[])
            if isinstance(sigs,str): sigs=[s.strip() for s in sigs.split(";") if s.strip()]
            if sigs: st.markdown(signal_tags(sigs),unsafe_allow_html=True)
