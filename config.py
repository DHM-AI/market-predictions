from dotenv import load_dotenv
import os

load_dotenv()

# API keys
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
ALPHA_VANTAGE_KEY = os.getenv("ALPHA_VANTAGE_KEY", "")
GMAIL_USER = os.getenv("GMAIL_USER", "")
GMAIL_APP_PASS = os.getenv("GMAIL_APP_PASS", "")
ALERT_EMAIL = os.getenv("ALERT_EMAIL", "renato@deltahubmedia.com")

# Supabase
SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")

# Universe
FUTURES = ["ES=F", "NQ=F", "RTY=F", "CL=F", "GC=F", "ZB=F"]

# Signal thresholds
BB_SQUEEZE_PERCENTILE = 10       # BB width below this percentile (0-100) triggers squeeze
ATR_COMPRESSION_RATIO = 0.75     # Current ATR / 50d avg ATR below this triggers compression
VOLUME_SURGE_RATIO = 2.0         # Volume > X times 20d avg triggers surge
RSI_OVERBOUGHT = 72
RSI_OVERSOLD = 28
EARNINGS_PROXIMITY_DAYS = 10     # Days until earnings to apply earnings catalyst logic

# Scoring weights (must sum to 100)
WEIGHTS = {
    "bb_squeeze": 25,
    "atr_compression": 15,
    "volume_surge": 20,
    "sentiment_spike": 20,
    "rsi_extreme": 10,
    "earnings_proximity": 10,
}

# Prediction
MIN_SCORE_TO_ALERT = 50          # Minimum composite score to include in output
TOP_N_CLAUDE_ANALYSIS = 5        # Number of top picks to send to Claude for explanation
MOVE_TARGET_PCT = 0.05           # 5% move target

# Model blending weights (must sum to 1.0)
XGB_WEIGHT = 0.70
SENTIMENT_WEIGHT = 0.30

# Paths
LOGS_DIR = "logs"
PREDICTIONS_CSV = "logs/predictions.csv"
MODEL_PATH = "model/saved/xgb_model.pkl"
FEATURE_NAMES_PATH = "model/saved/feature_names.json"

# Scheduler
SCAN_TIME_ET = "08:00"           # Daily scan time (local machine time, set to ET)

# Training
TRAIN_YEARS = 3                  # Years of history to pull for model training
TRAIN_TEST_SPLIT = 0.80          # Walk-forward split ratio
