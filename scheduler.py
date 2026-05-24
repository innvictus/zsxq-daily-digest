#!/usr/bin/env python3
"""Simple daily scheduler for Docker deployment."""
import os
import sys
import time
import subprocess
from datetime import datetime, timedelta


def get_next_run(hour: int, minute: int) -> datetime:
    now = datetime.now()
    next_run = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
    if next_run <= now:
        next_run += timedelta(days=1)
    return next_run


def run_job():
    print(f"\n{'='*50}")
    print(f"[{datetime.now():%Y-%m-%d %H:%M:%S}] Starting daily job...")
    print(f"{'='*50}")

    result = subprocess.run(
        [sys.executable, "main.py", "run"],
        capture_output=False,
        text=True,
    )
    return result.returncode


def main():
    run_hour = int(os.environ.get("RUN_HOUR", 1))
    run_minute = int(os.environ.get("RUN_MINUTE", 0))

    # Run immediately on startup (optional)
    run_on_start = os.environ.get("RUN_ON_START", "false").lower() == "true"
    if run_on_start:
        print("Running job on startup...")
        run_job()

    print(f"\nScheduler started. Will run daily at {run_hour:02d}:{run_minute:02d}.")

    while True:
        next_run = get_next_run(run_hour, run_minute)
        wait_seconds = (next_run - datetime.now()).total_seconds()

        print(f"Next run: {next_run:%Y-%m-%d %H:%M:%S} "
              f"(in {wait_seconds/3600:.1f} hours)")

        # Sleep in 60-second intervals, recheck time
        while wait_seconds > 0:
            sleep_time = min(60, wait_seconds)
            time.sleep(sleep_time)
            wait_seconds = (next_run - datetime.now()).total_seconds()

        # Run the job
        try:
            exit_code = run_job()
            if exit_code != 0:
                print(f"Job failed with exit code {exit_code}")
        except Exception as e:
            print(f"Job error: {e}")

        # Brief pause before recalculating next run
        time.sleep(10)


if __name__ == "__main__":
    main()
