"""
Anomaly detection.

Two kinds of checks:
  1. Fixed-threshold checks (e.g. delinquent stake % above X, slot time
     above Y ms) — config.ANOMALY_THRESHOLDS.
  2. Rolling-baseline checks (e.g. TPS dropped/spiked vs. the trailing
     average of the last N snapshots) — computed from history.jsonl.

Each detected anomaly is a dict: {severity, metric, message, value, baseline}
severity is one of "info", "warning", "critical".
"""

import json
import os

from . import config


def _load_recent_history(n=20):
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
    return entries[-n:]


def _pct_change(current, baseline):
    if baseline in (None, 0) or current is None:
        return None
    return 100 * (current - baseline) / baseline


def detect(report):
    """report: the full assembled report dict for this snapshot."""
    anomalies = []
    th = config.ANOMALY_THRESHOLDS
    history = _load_recent_history(n=20)

    # ---- TPS drop/spike vs rolling baseline -------------------------------
    net = report.get("network_performance", {})
    current_tps = net.get("avg_tps")
    past_tps_values = [
        h.get("network_performance", {}).get("avg_tps")
        for h in history
        if h.get("network_performance", {}).get("avg_tps") is not None
    ]
    if current_tps is not None and past_tps_values:
        baseline_tps = sum(past_tps_values) / len(past_tps_values)
        change = _pct_change(current_tps, baseline_tps)
        if change is not None:
            if change <= -th["tps_drop_pct"]:
                anomalies.append({
                    "severity": "warning",
                    "metric": "avg_tps",
                    "message": f"TPS dropped {abs(change):.1f}% vs. recent baseline "
                               f"({current_tps:.0f} vs. ~{baseline_tps:.0f})",
                    "value": current_tps,
                    "baseline": round(baseline_tps, 2),
                })
            elif change >= th["tps_spike_pct"]:
                anomalies.append({
                    "severity": "info",
                    "metric": "avg_tps",
                    "message": f"TPS spiked {change:.1f}% vs. recent baseline "
                               f"({current_tps:.0f} vs. ~{baseline_tps:.0f})",
                    "value": current_tps,
                    "baseline": round(baseline_tps, 2),
                })

    # ---- Slow slot times ----------------------------------------------------
    slot_time = net.get("avg_slot_time_ms")
    if slot_time is not None and slot_time >= th["slot_time_ms_warn"]:
        anomalies.append({
            "severity": "warning",
            "metric": "avg_slot_time_ms",
            "message": f"Average slot time is elevated at {slot_time:.0f}ms "
                       f"(target ~400ms)",
            "value": slot_time,
            "baseline": 400,
        })

    # ---- Validator delinquency ----------------------------------------------
    validators = report.get("validators", {})
    delinquent_stake_pct = validators.get("delinquent_stake_pct")
    if delinquent_stake_pct is not None:
        if delinquent_stake_pct >= th["delinquent_stake_pct_critical"]:
            anomalies.append({
                "severity": "critical",
                "metric": "delinquent_stake_pct",
                "message": f"{delinquent_stake_pct:.2f}% of active stake is "
                           f"delinquent (critical threshold "
                           f"{th['delinquent_stake_pct_critical']}%)",
                "value": delinquent_stake_pct,
                "baseline": th["delinquent_stake_pct_critical"],
            })
        elif delinquent_stake_pct >= th["delinquent_stake_pct_warn"]:
            anomalies.append({
                "severity": "warning",
                "metric": "delinquent_stake_pct",
                "message": f"{delinquent_stake_pct:.2f}% of active stake is "
                           f"delinquent (warn threshold "
                           f"{th['delinquent_stake_pct_warn']}%)",
                "value": delinquent_stake_pct,
                "baseline": th["delinquent_stake_pct_warn"],
            })

    # ---- TVL move -------------------------------------------------------------
    tvl = report.get("defi", {}).get("tvl", {})
    tvl_change = tvl.get("tvl_change_pct_24h")
    if tvl_change is not None and abs(tvl_change) >= th["tvl_change_pct_24h"]:
        direction = "up" if tvl_change > 0 else "down"
        anomalies.append({
            "severity": "info" if abs(tvl_change) < 20 else "warning",
            "metric": "tvl_change_pct_24h",
            "message": f"Solana TVL is {direction} {abs(tvl_change):.1f}% in 24h",
            "value": tvl_change,
            "baseline": 0,
        })

    # ---- SOL price move ---------------------------------------------------
    price = report.get("market", {}).get("price", {})
    price_change_24h = price.get("price_change_pct_24h")
    if price_change_24h is not None and abs(price_change_24h) >= th["sol_price_change_pct_24h"]:
        direction = "up" if price_change_24h > 0 else "down"
        anomalies.append({
            "severity": "info" if abs(price_change_24h) < 15 else "warning",
            "metric": "sol_price_change_pct_24h",
            "message": f"SOL price is {direction} {abs(price_change_24h):.1f}% in 24h",
            "value": price_change_24h,
            "baseline": 0,
        })

    # ---- Health check -------------------------------------------------------
    if net.get("health") not in (None, "ok"):
        anomalies.append({
            "severity": "critical",
            "metric": "rpc_health",
            "message": f"RPC node health check did not return 'ok': {net.get('health')}",
            "value": net.get("health"),
            "baseline": "ok",
        })

    return anomalies
