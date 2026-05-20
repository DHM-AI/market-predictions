"""
Keeps the agent running on a daily schedule.

Usage:
    python scheduler.py

Runs agent.py every weekday at the time defined in config.SCAN_TIME_ET.
Keep this process alive (e.g. via nohup or a launchd plist).
"""
import schedule
import time
from datetime import datetime
from agent import run_scan
from config import SCAN_TIME_ET


def _is_weekday() -> bool:
    return datetime.today().weekday() < 5  # Mon–Fri


def scheduled_job():
    if _is_weekday():
        print(f"[scheduler] Triggering scan at {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        run_scan(send_email=True)
    else:
        print(f"[scheduler] Weekend — skipping scan.")


schedule.every().day.at(SCAN_TIME_ET).do(scheduled_job)

print(f"[scheduler] Agent scheduled daily at {SCAN_TIME_ET}. Press Ctrl+C to stop.")
print(f"[scheduler] Next run: {schedule.next_run()}")

while True:
    schedule.run_pending()
    time.sleep(30)
