"""Assemble collectors into one report and maintain rolling history."""

import datetime
import json
import os
import time

from . import config
from .assemble_helpers import build_outlook
from .collectors import solana_rpc, defillama, coingecko, solana_data_site, twitter_feed, solana_status, dune


def build_report():
    generated_at = datetime.datetime.now(datetime.timezone.utc)
    market = coingecko.collect_all()
    defi = defillama.collect_all()
    validators = solana_rpc.collect_validators()
    network = solana_rpc.collect_network_performance()
    active_sample = solana_rpc.collect_active_wallets_sample()
    dune_activity = dune.collect_daily_active_addresses()

    report = {
        "meta": {
            "generated_at_utc": generated_at.isoformat(),
            "generated_at_unix": int(generated_at.timestamp()),
            "generator": "SolBeat",
            "version": "1.1",
        },
        "network_performance": network,
        "validators": validators,
        "supply": solana_rpc.collect_supply(),
        "active_wallets_sample": active_sample,
        "daily_active_addresses": dune_activity,
        "defi": defi,
        "market": market,
        "ecosystem_site": solana_data_site.collect(),
        "social": twitter_feed.collect(),
        "upcoming": _static_upcoming_notes(),
        "solana_network_status": {
            "current": solana_status.collect_current_status(),
            "incident_history": solana_status.collect_days_since_last_incident(),
        },
        "long_history": {},
    }
    report["long_history"] = _build_long_history()
    report["outlook"] = build_outlook(report)
    return report


def _build_long_history():
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
    return [
        {
            "name": "Alpenglow",
            "description": "Consensus overhaul work targeting much faster finality; activation work is advancing through Agave releases and feature gates.",
            "track": "https://github.com/solana-foundation/solana-improvement-documents",
        },
        {
            "name": "SIMD / fee-market changes",
            "description": "Ongoing protocol proposals covering resource and inclusion fees, block capacity, and other economic mechanics.",
            "track": "https://github.com/solana-foundation/solana-improvement-documents/pulls",
        },
        {
            "name": "Firedancer",
            "description": "Independent validator client development continues, improving client diversity and the network's performance ceiling.",
            "track": "https://github.com/firedancer-io/firedancer",
        },
    ]


def append_history(report):
    os.makedirs(config.OUTPUT_DIR, exist_ok=True)
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
            "tvl": {"tvl_usd": report.get("defi", {}).get("tvl", {}).get("tvl_usd")},
            "stablecoins": {"total_stablecoin_supply_usd": report.get("defi", {}).get("stablecoins", {}).get("total_stablecoin_supply_usd")},
            "dex_volume": {"dex_volume_24h_usd": report.get("defi", {}).get("dex_volume", {}).get("dex_volume_24h_usd")},
            "fees_and_rev": {"chain_revenue_24h_usd": report.get("defi", {}).get("fees_and_rev", {}).get("chain_revenue_24h_usd")},
        },
        "market": {"price": {
            "price_usd": report.get("market", {}).get("price", {}).get("price_usd"),
            "market_cap_usd": report.get("market", {}).get("price", {}).get("market_cap_usd"),
            "volume_24h_usd": report.get("market", {}).get("price", {}).get("volume_24h_usd"),
        }},
        "supply": {"total_sol": report.get("supply", {}).get("total_sol")},
        "active_wallets_sample": {"unique_wallets_in_block": report.get("active_wallets_sample", {}).get("unique_wallets_in_block")},
        "daily_active_addresses": {"value": report.get("daily_active_addresses", {}).get("value")},
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
            try:
                if line.strip():
                    entries.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return entries


def _downsample_history(entries):
    if not entries:
        return entries
    now = time.time()
    recent, hourly_bucket, daily_bucket = [], {}, {}
    for entry in entries:
        ts = entry.get("generated_at_unix")
        if ts is None:
            continue
        age = now - ts
        if age <= config.HISTORY_FULL_RES_SECONDS:
            recent.append(entry)
        elif age <= config.HISTORY_HOURLY_RES_SECONDS:
            hourly_bucket.setdefault(int(ts // 3600), entry)
        elif age <= config.HISTORY_DAILY_RES_SECONDS:
            daily_bucket.setdefault(int(ts // 86400), entry)
    combined = list(daily_bucket.values()) + list(hourly_bucket.values()) + recent
    combined.sort(key=lambda e: e.get("generated_at_unix", 0))
    return combined[-config.HISTORY_ABSOLUTE_MAX_ENTRIES:]
