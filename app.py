import streamlit as st

st.set_page_config(
    page_title="Market Predictions",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.title("Market Predictions Agent")
st.markdown(
    "A daily scanner that identifies stocks and futures likely to move **5-10%+** "
    "using technicals, news sentiment, and an XGBoost classifier trained on 3 years of history."
)

col1, col2, col3 = st.columns(3)
col1.page_link("pages/1_Scanner.py", label="Scanner", icon="🔍")
col2.page_link("pages/2_Ticker_Dive.py", label="Ticker Deep Dive", icon="📊")
col3.page_link("pages/3_Track_Record.py", label="Track Record", icon="📋")

st.divider()
st.markdown("""
### Getting started

1. **Train the model** (first time only):
   ```bash
   python -m model.trainer
   ```
   Downloads 3 years of S&P 500 history and trains the XGBoost classifier. Takes ~20-30 min.

2. **Run the scanner**:
   ```bash
   python agent.py
   ```
   Or click **Run Scan** inside the Scanner page.

3. **Schedule daily scans** (optional):
   ```bash
   python scheduler.py
   ```
   Runs automatically every weekday at the time set in `config.py`.

4. **Set up alerts** — copy `.env.example` to `.env` and fill in your API keys and Gmail credentials.
""")
