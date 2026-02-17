# Stock Market Research Agent v3

AI-powered stock research with Polymarket prediction signals, insider tracking, scoring, and automated alerts.


## What's in v3

- Polymarket prediction market data (Fed rates, recession odds, tariffs, etc.)
- Insider transaction tracking
- Short interest monitoring
- Analyst estimates and price targets
- Macro context (S&P 500, VIX, yields, sector performance)
- 1-10 scoring system across 9 categories
- Alert scanner with email and text notifications
- Auto-scan mode (runs every few hours on your PC)


## Quick Start

1. Delete your old stock-agent files (keep the .git folder if you see it)
2. Copy these new files into the stock-agent folder
3. Open config.py and paste your API key
4. In VS Code terminal:

    pip install -r requirements.txt
    streamlit run app.py


## Commands

    streamlit run app.py                 - Web interface
    python main.py analyze AAPL          - Full analysis
    python main.py daily                 - Analyze watchlist
    python main.py scan                  - Quick alert scan (free)
    python auto_scan.py                  - Auto-scan every 4 hours


## Updating Streamlit

After changing any files:

    git add .
    git commit -m "description of change"
    git push

Streamlit auto-redeploys within a minute.


## Setting Up Email Alerts

1. Go to myaccount.google.com > Security > 2-Step Verification > App passwords
2. Create an app password for "Mail"
3. Add to Streamlit secrets (Advanced Settings on your app):
   GMAIL_ADDRESS = "you@gmail.com"
   GMAIL_APP_PASSWORD = "xxxx xxxx xxxx xxxx"
   ALERT_EMAIL = "you@gmail.com"


## Setting Up Text Alerts

1. Sign up at twilio.com (free trial = $15 credit)
2. Get a phone number
3. Add to Streamlit secrets:
   TWILIO_SID = "your-sid"
   TWILIO_AUTH = "your-token"
   TWILIO_FROM = "+1234567890"
   ALERT_PHONE = "+1234567890"


## Cost

- Full analysis: ~$0.15-0.20 per stock
- Alert scan: Free
- Auto-scan: Free
- Polymarket data: Free
