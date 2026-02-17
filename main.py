"""
Stock Market Research Agent v3
==============================
Usage:
    python main.py analyze AAPL          - Full analysis with Polymarket + scoring
    python main.py daily                 - Analyze all stocks in watchlist
    python main.py daily AAPL MSFT NVDA  - Analyze specific tickers
    python main.py scan                  - Quick alert scan (free, no AI)
    python main.py scan AAPL TSLA        - Scan specific tickers

Web interface:
    streamlit run app.py

Auto-scan (runs every 4 hours while your PC is on):
    python auto_scan.py
"""

import sys
from pathlib import Path
from datetime import date

from orchestrator import analyze_stock, run_daily_research, run_alert_scan
from tools.cache import init_cache
from config import WATCHLIST


def save_report(ticker, report, output_dir):
    filepath = output_dir / f"{ticker}_{date.today()}.md"
    filepath.write_text(report, encoding="utf-8")
    return filepath


def cmd_analyze(ticker):
    print(f"Analyzing {ticker}...\n")
    report = analyze_stock(ticker)
    if not report or not report.strip():
        print("ERROR: Empty report. Try again.")
        return
    output_dir = Path("reports")
    output_dir.mkdir(exist_ok=True)
    filepath = save_report(ticker, report, output_dir)
    print(f"\nReport saved to {filepath}")
    print("-" * 50)
    preview = report[:500]
    if len(report) > 500:
        preview += "...\n\n(Open the file in reports/ to see full report)"
    print(preview)


def cmd_daily(tickers=None):
    watchlist = tickers or WATCHLIST
    print(f"Daily research for {len(watchlist)} stocks: {', '.join(watchlist)}\n")
    reports = run_daily_research(watchlist)
    output_dir = Path("reports")
    output_dir.mkdir(exist_ok=True)
    saved = 0
    for ticker, report in reports.items():
        if report and report.strip():
            filepath = save_report(ticker, report, output_dir)
            print(f"  Saved: {filepath}")
            saved += 1
    print(f"\nDone! {saved}/{len(reports)} reports saved.")


def cmd_scan(tickers=None):
    watchlist = tickers or WATCHLIST
    print(f"Scanning {len(watchlist)} stocks: {', '.join(watchlist)}\n")
    alerts = run_alert_scan(watchlist)
    if alerts:
        print(f"\n{'='*50}")
        print(f"  {len(alerts)} ALERTS FOUND")
        print(f"{'='*50}\n")
        for a in alerts:
            icon = "!!" if a.severity == "high" else "--"
            print(f"  {icon} [{a.alert_type}] {a.message}")
    else:
        print("\nAll clear. No alerts.")


def main():
    init_cache()
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    command = sys.argv[1].lower()

    if command == "analyze":
        if len(sys.argv) < 3:
            print("Usage: python main.py analyze TICKER")
            sys.exit(1)
        cmd_analyze(sys.argv[2].upper())
    elif command == "daily":
        tickers = [t.upper() for t in sys.argv[2:]] if len(sys.argv) > 2 else None
        cmd_daily(tickers)
    elif command == "scan":
        tickers = [t.upper() for t in sys.argv[2:]] if len(sys.argv) > 2 else None
        cmd_scan(tickers)
    else:
        print(f"Unknown command: '{command}'")
        sys.exit(1)


if __name__ == "__main__":
    main()
