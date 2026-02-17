import os

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "PASTE-YOUR-KEY-HERE")
NEWS_API_KEY = os.environ.get("NEWS_API_KEY", "")
FMP_API_KEY = ""
TWILIO_SID = os.environ.get("TWILIO_SID", "")
TWILIO_AUTH = os.environ.get("TWILIO_AUTH", "")
TWILIO_FROM = os.environ.get("TWILIO_FROM", "")
ALERT_PHONE = os.environ.get("ALERT_PHONE", "")
ALERT_EMAIL = os.environ.get("ALERT_EMAIL", "")
GMAIL_ADDRESS = os.environ.get("GMAIL_ADDRESS", "")
GMAIL_APP_PASSWORD = os.environ.get("GMAIL_APP_PASSWORD", "")

try:
    import streamlit as st
    if hasattr(st, "secrets"):
        ANTHROPIC_API_KEY = st.secrets["ANTHROPIC_API_KEY"]
except Exception:
    pass

MODEL_FAST = "claude-sonnet-4-5-20250929"
MODEL_DEEP = "claude-opus-4-6"
WATCHLIST = ["HOOD", "NFLX", "PLTR", "AMZN", "META"]
MAX_DAILY_SPEND_USD = 3.00
MAX_TOKENS_PER_STOCK = 80_000
ALERT_PRICE_DROP_PCT = 5.0
ALERT_PRICE_SPIKE_PCT = 5.0
ALERT_VOLUME_MULTIPLIER = 2.0
ALERT_INSIDER_BUY_MIN = 100_000
ALERT_SHORT_INTEREST_PCT = 20.0
AUTO_SCAN_INTERVAL_HOURS = 4
