import streamlit as st

# Page config MUST be set on the entry page so the sidebar is collapsed
# and there's no flash of the default Streamlit nav before the redirect.
st.set_page_config(
    page_title="Illuminati",
    page_icon="🔺",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# Hide Streamlit chrome during the brief redirect so the user doesn't
# see a black flash with the sidebar showing.
st.markdown("""
<style>
  [data-testid="stSidebar"], [data-testid="stHeader"], #MainMenu, footer { display: none !important; }
  .block-container { padding: 0 !important; }
  body, .stApp { background: #03060d !important; }
  .loader {
    position: fixed; inset: 0; display: flex; align-items: center; justify-content: center;
    flex-direction: column; gap: 16px; background: #03060d; z-index: 9999;
  }
  .loader-ring {
    width: 44px; height: 44px; border-radius: 50%;
    border: 2px solid rgba(0,212,255,0.15);
    border-top-color: #00d4ff;
    animation: spin 0.9s linear infinite;
    box-shadow: 0 0 30px rgba(0,212,255,0.35);
  }
  .loader-text {
    font-family: 'JetBrains Mono', monospace; font-size: 11px;
    letter-spacing: 4px; color: #00d4ff; text-transform: uppercase;
    text-shadow: 0 0 10px rgba(0,212,255,0.5);
  }
  @keyframes spin { to { transform: rotate(360deg); } }
</style>
<div class="loader">
  <div class="loader-ring"></div>
  <div class="loader-text">ILLUMINATI · INITIALIZING</div>
</div>
""", unsafe_allow_html=True)

# Redirect home → Scanner (the main experience)
st.switch_page("pages/1_Scanner.py")
