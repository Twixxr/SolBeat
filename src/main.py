"""
SolPulse Canada — main entrypoint.

Usage:
    python -m src.main                 # generate one snapshot and exit
    python -m src.main --loop          # run continuously, refreshing on config interval
    python -m src.main --loop --interval 15   # refresh every 15 minutes

Outputs (see src/config.py to change paths):
    data/latest.json     — machine-readable, full report + anomalies
    data/latest.md       — human-readable Markdown report
    data/history.jsonl   — rolling append-only history used for anomaly baselines
    dashboard/data.json  — same payload as latest.json, served to the HTML dashboard
"""

import argparse
import json
import os
import sys
import time
import traceback

from . import config
from .assemble import build_report, append_history
from .anomaly import detect
from .report.build_markdown import render as render_markdown


def _load_history_series():
    """
    Full time series from history.jsonl, for the dashboard's expandable
    history charts. No trimming needed here — history.jsonl is already
    kept bounded by assemble._downsample_history's tiered retention
    (full resolution for 48h, hourly for 30 days, daily for up to 180
    days), so this naturally covers up to ~6 months per metric while
    staying a reasonable size (at most a few thousand entries).
    """
    if not os.path.exists(config.HISTORY_FILE):
        return []
    entries = []
    with open(config.HISTORY_FILE, "r") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entries.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return entries


def run_once():
    print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Collecting Solana ecosystem data…")

    report = build_report()
    anomalies = detect(report)  # computed BEFORE appending this snapshot to history
    append_history(report)

    os.makedirs(config.OUTPUT_DIR, exist_ok=True)
    os.makedirs(config.DASHBOARD_DIR, exist_ok=True)

    payload = {"report": report, "anomalies": anomalies, "history_series": _load_history_series()}

    with open(config.LATEST_JSON, "w") as f:
        json.dump(payload, f, indent=2, default=str)

    with open(config.LATEST_MD, "w") as f:
        f.write(render_markdown(report, anomalies))

    # Dashboard reads this file client-side (see dashboard/index.html)
    with open(config.DASHBOARD_DATA_JSON, "w") as f:
        json.dump(payload, f, indent=2, default=str)

    n_crit = sum(1 for a in anomalies if a["severity"] == "critical")
    n_warn = sum(1 for a in anomalies if a["severity"] == "warning")
    n_info = sum(1 for a in anomalies if a["severity"] == "info")
    print(f"  -> wrote {config.LATEST_JSON}")
    print(f"  -> wrote {config.LATEST_MD}")
    print(f"  -> wrote {config.DASHBOARD_DATA_JSON}")
    print(f"  -> anomalies: {n_crit} critical, {n_warn} warning, {n_info} info")
    return payload


def main():
    parser = argparse.ArgumentParser(description="Generate the SolPulse Canada Solana ecosystem report.")
    parser.add_argument("--loop", action="store_true", help="Run continuously instead of once.")
    parser.add_argument(
        "--interval", type=int, default=config.DEFAULT_REFRESH_INTERVAL_MINUTES,
        help=f"Minutes between refreshes in --loop mode (default: {config.DEFAULT_REFRESH_INTERVAL_MINUTES})."
    )
    args = parser.parse_args()

    if not args.loop:
        run_once()
        return

    print(f"Running in loop mode, refreshing every {args.interval} minute(s). Ctrl+C to stop.")
    while True:
        try:
            run_once()
        except Exception:
            # Never let one bad cycle kill a long-running process.
            print("Snapshot failed, will retry next interval:", file=sys.stderr)
            traceback.print_exc()
        time.sleep(args.interval * 60)


if __name__ == "__main__":
    main()
