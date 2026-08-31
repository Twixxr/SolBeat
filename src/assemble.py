"""
Pulls all collectors together into one report dict, and manages the
rolling history.jsonl file used for anomaly baselines.
"""

import json
import os
import time
import datetime

from . import config
from .collectors import solana_rpc, defillama, coingecko, solana_data_site, twitter_feed, solana_status


def build_report():
    generated_at = datetime.datetime.now(datetime.timezone.utc)

    report = {
        "meta": {
            "generated_at_utc": generated_at.isoformat(),
            "generated_at_unix": int(generated_at.timestamp()),
            "generator": "SolPulse Canada",
            "version": "1.0",
        },
        "network_performance": solana_rpc.collect_network_performance(),
        "validators": solana_rpc.collect_validators(),
        "supply": solana_rpc.collect_supply(),
        "active_wallets_sample": solana_rpc.collect_active_wallets_sample(),
        "defi": defillama.collect_all(),
        "market": coingecko.collect_all(),
        "ecosystem_site": solana_data_site.collect(),
        "social": twitter_feed.collect(),
        "upcoming": _static_upcoming_notes(),
        "solana_network_status": {
            "current": solana_status.collect_current_status(),
            "incident_history": solana_status.collect_days_since_last_incident(),
        },
        "long_history": _build_long_history(),
        "report_uptime": _compute_report_uptime(),
    }
    return report


def _compute_report_uptime():
    """
    'Uptime' here means how long this SolBeat pipeline has run without
    missing a scheduled refresh — NOT Solana network uptime, which has no
    public keyless data source (Solana's own status page has no documented
    public API this project relies on). Computed by scanning this project's
    own history.jsonl for gaps larger than a generous multiple of the
    expected refresh interval, which would indicate the GitHub Action
    failed, was disabled, or GitHub itself had an outage.
    """
    if not os.path.exists(config.HISTORY_FILE):
        return {"days": 0.0, "since_unix": int(time.time()), "note": "no history yet"}

    timestamps = []
    with open(config.HISTORY_FILE, "r") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                continue
            ts = entry.get("generated_at_unix")
            if ts:
                timestamps.append(ts)

    if not timestamps:
        return {"days": 0.0, "since_unix": int(time.time()), "note": "no history yet"}

    timestamps.sort()
    now = int(time.time())
    gap_threshold_seconds = config.DEFAULT_REFRESH_INTERVAL_MINUTES * 60 * 3  # generous tolerance

    last_gap_end = None
    for i in range(1, len(timestamps)):
        gap = timestamps[i] - timestamps[i - 1]
        if gap > gap_threshold_seconds:
            last_gap_end = timestamps[i]

    if last_gap_end is not None:
        since_unix = last_gap_end
        note = "since last missed refresh"
    else:
        since_unix = timestamps[0]
        note = "since tracking began"

    days = round((now - since_unix) / 86400, 2)
    return {"days": days, "since_unix": since_unix, "note": note}


def _build_long_history():
    """
    Multi-year daily history for the dashboard's expanded charts, pulled
    fresh each run from DeFiLlama (TVL, stablecoin supply, DEX volume,
    chain revenue — full history, no key needed) and CoinGecko (price,
    market cap, volume — best-effort ~2 years). Metrics with no long-run
    keyless source (TPS, slot time, validator count, SOL supply) are NOT
    here — the dashboard falls back to this project's own rolling
    history.jsonl for those, clearly labeled as starting from whenever
    this report first went live.
    """
    cg_long = coingecko.collect_long_history()
    return {
        "price": cg_long.get("price", {}),
        "market_cap": cg_long.get("market_cap", {}),
        "volume": cg_long.get("volume", {}),
        "tvl": defillama.collect_tvl_history(),
        "stablecoin_supply": defillama.collect_stablecoin_history(),
        "dex_volume": defillama.collect_dex_volume_history(),
        "chain_revenue": defillama.collect_fees_history(),
    }


def _static_upcoming_notes():
    """
    Curated pointers to major in-flight Solana upgrades/proposals. These
    move slowly (months), so they're maintained as a short curated list
    rather than scraped, with links so readers can check current status.
    Update this list periodically — it's the one manually-maintained part
    of an otherwise fully automated report.
    """
    return [
        {
            "name": "Alpenglow",
            "description": "Proposed consensus overhaul (Votor + Rotor) targeting ~100-150ms "
                            "finality, replacing TowerBFT/Turbine-era assumptions.",
            "track": "https://github.com/solana-foundation/solana-improvement-documents",
        },
        {
            "name": "SIMD-related fee market / tokenomics changes",
            "description": "Ongoing SIMD proposals affecting base fee burn, priority fees, "
                            "and inflation schedule. Check the SIMD repo for the current "
                            "numbered proposal under active discussion.",
            "track": "https://github.com/solana-foundation/solana-improvement-documents/pulls",
        },
        {
            "name": "Firedancer",
            "description": "Independent validator client (Jump Crypto) aimed at client "
                            "diversity and higher throughput ceilings; rolling out in stages "
                            "across mainnet-beta.",
            "track": "https://github.com/firedancer-io/firedancer",
        },
    ]


def append_history(report):
    os.makedirs(config.OUTPUT_DIR, exist_ok=True)
    # Keep a slimmed-down snapshot in history — only the fields the
    # dashboard's expandable history charts and anomaly.py's baselines
    # actually need, not the full report.
    slim = {
        "generated_at_unix": report["meta"]["generated_at_unix"],
        "network_performance": {
            "avg_tps": report.get("network_performance", {}).get("avg_tps"),
            "avg_slot_time_ms": report.get("network_performance", {}).get("avg_slot_time_ms"),
        },
        "validators": {
            "delinquent_stake_pct": report.get("validators", {}).get("delinquent_stake_pct"),
            "active_count": report.get("validators", {}).get("active_count"),
        },
        "defi": {
            "tvl": {
                "tvl_usd": report.get("defi", {}).get("tvl", {}).get("tvl_usd"),
            },
            "stablecoins": {
                "total_stablecoin_supply_usd": report.get("defi", {}).get("stablecoins", {}).get("total_stablecoin_supply_usd"),
            },
            "dex_volume": {
                "dex_volume_24h_usd": report.get("defi", {}).get("dex_volume", {}).get("dex_volume_24h_usd"),
            },
            "fees_and_rev": {
                "chain_revenue_24h_usd": report.get("defi", {}).get("fees_and_rev", {}).get("chain_revenue_24h_usd"),
            },
        },
        "market": {
            "price": {
                "price_usd": report.get("market", {}).get("price", {}).get("price_usd"),
                "market_cap_usd": report.get("market", {}).get("price", {}).get("market_cap_usd"),
                "volume_24h_usd": report.get("market", {}).get("price", {}).get("volume_24h_usd"),
            },
        },
        "supply": {
            "total_sol": report.get("supply", {}).get("total_sol"),
        },
        "active_wallets_sample": {
            "unique_wallets_in_block": report.get("active_wallets_sample", {}).get("unique_wallets_in_block"),
        },
    }

    entries = _read_history_entries()
    entries.append(slim)
    entries = _downsample_history(entries)

    with open(config.HISTORY_FILE, "w") as f:
        for entry in entries:
            f.write(json.dumps(entry) + "\n")


def _read_history_entries():
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


def _downsample_history(entries):
    """
    Tiered retention so history.jsonl gives genuinely long-term history for
    EVERY tracked metric — including the ones with no external long-run
    source (TPS, slot time, validator count, SOL supply, active wallets
    sample) — while staying bounded in size forever, regardless of refresh
    frequency:

      - Last 48h:        every entry kept (full resolution)
      - 48h to 30 days:  at most one entry per hour
      - 30 to 180 days:  at most one entry per day
      - Older than 180 days: dropped

    This keeps the file to roughly (48h / interval) + 720 + 150 entries at
    most — a few thousand even at a 5-minute refresh interval — while still
    covering a full 6 months of history.
    """
    if not entries:
        return entries

    now = time.time()
    recent = []
    hourly_bucket = {}
    daily_bucket = {}

    for entry in entries:
        ts = entry.get("generated_at_unix")
        if ts is None:
            continue
        age = now - ts
        if age <= config.HISTORY_FULL_RES_SECONDS:
            recent.append(entry)
        elif age <= config.HISTORY_HOURLY_RES_SECONDS:
            bucket_key = int(ts // 3600)
            hourly_bucket.setdefault(bucket_key, entry)
        elif age <= config.HISTORY_DAILY_RES_SECONDS:
            bucket_key = int(ts // 86400)
            daily_bucket.setdefault(bucket_key, entry)
        # else: older than the daily-resolution window — dropped entirely.

    combined = list(daily_bucket.values()) + list(hourly_bucket.values()) + recent
    combined.sort(key=lambda e: e.get("generated_at_unix", 0))

    # Hard safety cap in case of unexpectedly frequent refreshes blowing up
    # the "recent" (full-resolution) tier beyond what's reasonable.
    if len(combined) > config.HISTORY_ABSOLUTE_MAX_ENTRIES:
        combined = combined[-config.HISTORY_ABSOLUTE_MAX_ENTRIES:]

    return combined
