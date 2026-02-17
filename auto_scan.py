"""
Auto Alert Scanner
==================
Runs an alert scan every few hours while your PC is on.
Checks your watchlist for actionable signals and sends
email/text notifications if anything triggers.

To run:
    python auto_scan.py

To stop: press Ctrl+C

This does NOT use Claude / does NOT cost API money.
It only fetches free data from Yahoo Finance and checks
your alert thresholds.

To change how often it runs, edit AUTO_SCAN_INTERVAL_HOURS
in config.py (default: every 4 hours).
"""

import time
import schedule
from datetime import datetime

from orchestrator import run_alert_scan
from tools.cache import init_cache
from config import WATCHLIST, AUTO_SCAN_INTERVAL_HOURS


def run_scan():
    """Run one alert scan."""
    print(f"\n{'='*50}")
    print(f"  ALERT SCAN - {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"{'='*50}\n")

    try:
        alerts = run_alert_scan(WATCHLIST)

        if alerts:
            print(f"\n  >> {len(alerts)} alerts found and notifications sent!")
        else:
            print(f"\n  >> All clear. Next scan in {AUTO_SCAN_INTERVAL_HOURS} hours.")

    except Exception as e:
        print(f"\n  >> Scan error: {e}")
        print(f"  >> Will retry in {AUTO_SCAN_INTERVAL_HOURS} hours.")


def main():
    init_cache()

    print(__doc__)
    print(f"Watchlist: {', '.join(WATCHLIST)}")
    print(f"Scan interval: every {AUTO_SCAN_INTERVAL_HOURS} hours")
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"\nPress Ctrl+C to stop.\n")

    # Run immediately on start
    run_scan()

    # Then schedule recurring scans
    schedule.every(AUTO_SCAN_INTERVAL_HOURS).hours.do(run_scan)

    while True:
        schedule.run_pending()
        time.sleep(60)  # Check every minute


if __name__ == "__main__":
    main()
