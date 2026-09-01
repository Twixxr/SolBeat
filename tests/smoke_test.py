"""
Offline smoke test — mocks every network call so we can validate
assembly / anomaly detection / markdown rendering / JSON writing without
needing live network access. Not a substitute for a real run against live
endpoints, but catches structural bugs (KeyErrors, format-string issues,
etc.) cheaply.

Run: python3 tests/smoke_test.py
"""

import json
import os
import sys
import shutil
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from unittest import mock

# ---- Fixture data mimicking real API responses -----------------------------

FAKE_PERF_SAMPLES = [
    {"samplePeriodSecs": 60, "numTransactions": 240000, "numSlots": 150},
    {"samplePeriodSecs": 60, "numTransactions": 230000, "numSlots": 148},
    {"samplePeriodSecs": 60, "numTransactions": 60000, "numSlots": 150},  # induces a "drop" anomaly vs baseline
]

FAKE_VOTE_ACCOUNTS = {
    "current": [
        {"votePubkey": f"Vote{i}", "nodePubkey": f"Node{i}", "activatedStake": 10_000_000_000_000 - i * 1000,
         "commission": 5, "lastVote": 12345, "rootSlot": 12300}
        for i in range(30)
    ],
    "delinquent": [
        {"votePubkey": "VoteDelinquent1", "nodePubkey": "NodeD1", "activatedStake": 500_000_000_000,
         "commission": 10, "lastVote": 100, "rootSlot": 90}
    ],
}

FAKE_SUPPLY = {"value": {"total": 588_000_000_000_000_000, "circulating": 470_000_000_000_000_000,
                          "nonCirculating": 118_000_000_000_000_000}}

FAKE_BLOCK = {
    "transactions": [
        {"transaction": {"accountKeys": ["WalletA", "WalletX"]}},
        {"transaction": {"accountKeys": ["WalletB", "WalletY"]}},
        {"transaction": {"accountKeys": ["WalletA", "WalletZ"]}},  # WalletA repeats as fee payer -> unique count stays 2
    ]
}

FAKE_EPOCH_INFO = {"epoch": 600, "slotIndex": 123456, "slotsInEpoch": 432000, "blockHeight": 290_000_000}

FAKE_TVL_SERIES = [
    {"date": 1_700_000_000, "tvl": 4_000_000_000},
    {"date": 1_700_086_400, "tvl": 4_100_000_000},
    {"date": 1_700_600_000 - 604800, "tvl": 3_900_000_000},
    {"date": 1_700_600_000, "tvl": 4_500_000_000},
]

FAKE_STABLECOINS = [
    {"name": "Solana", "totalCirculatingUSD": {"peggedUSD": 8_500_000_000}},
    {"name": "Ethereum", "totalCirculatingUSD": {"peggedUSD": 90_000_000_000}},
]

FAKE_DEX_VOLUME = {
    "total24h": 1_200_000_000, "change_1d": 5.3,
    "protocols": [{"name": "Jupiter", "total24h": 700_000_000}, {"name": "Raydium", "total24h": 300_000_000}],
}

FAKE_FEES = {"total24h": 2_500_000, "change_1d": -3.1}

FAKE_PROTOCOLS = [
    {"name": "Jupiter", "category": "DEX Aggregator", "chainTvls": {"Solana": 900_000_000},
     "change_1d": 2.1, "url": "https://jup.ag"},
    {"name": "Kamino", "category": "Lending", "chainTvls": {"Solana": 600_000_000},
     "change_1d": -1.4, "url": "https://kamino.finance"},
    {"name": "Aave", "category": "Lending", "chainTvls": {"Ethereum": 5_000_000_000},
     "change_1d": 0.3, "url": "https://aave.com"},  # no Solana entry -> should be excluded
    {"name": "Binance CEX", "category": "CEX", "chainTvls": {"Solana": 2_000_000_000},
     "change_1d": 0.1, "url": "https://binance.com"},  # CEX -> should be excluded
]

FAKE_STAKEWIZ_VALIDATORS = [
    {"vote_identity": "Vote0", "name": "Test Validator Zero", "website": "https://twitter.com/testvalidator0"},
    {"vote_identity": "Vote1", "name": "Test Validator One", "website": "https://testvalidator1.io"},
]

FAKE_COINGECKO_PRICE = {"solana": {"usd": 210.5, "usd_24h_change": 12.4, "usd_24h_vol": 3_000_000_000,
                                    "usd_market_cap": 100_000_000_000}}
FAKE_COINGECKO_TREND = {"prices": [[1_700_000_000_000 + i * 86400000, 200 + i] for i in range(7)]}
FAKE_COINGECKO_LONG = {
    "prices": [[1_700_000_000_000 + i * 86400000, 150 + i] for i in range(30)],
    "market_caps": [[1_700_000_000_000 + i * 86400000, 70_000_000_000 + i * 1_000_000] for i in range(30)],
    "total_volumes": [[1_700_000_000_000 + i * 86400000, 2_000_000_000 + i * 10_000] for i in range(30)],
}
FAKE_STABLECOIN_CHART = [
    {"date": "1700000000", "totalCirculating": {"peggedUSD": 8_000_000_000}},
    {"date": "1700086400", "totalCirculating": {"peggedUSD": 8_100_000_000}},
]
FAKE_DEX_VOLUME_CHART = {"totalDataChart": [[1700000000, 1_100_000_000], [1700086400, 1_150_000_000]]}
FAKE_FEES_CHART = {"totalDataChart": [[1700000000, 2_400_000], [1700086400, 2_450_000]]}

FAKE_SOLANA_STATUS = {"page": {"id": "rm9mn997x8jd", "name": "Solana"}, "status": {"description": "All Systems Operational", "indicator": "none"}}
FAKE_SOLANA_INCIDENTS = {"page": {"id": "rm9mn997x8jd", "name": "Solana"}, "incidents": [
    {"id": "inc1", "name": "Elevated skip rate on mainnet-beta", "created_at": "2026-08-01T10:00:00Z", "resolved_at": "2026-08-01T14:00:00Z"},
    {"id": "inc2", "name": "Degraded performance", "created_at": "2026-07-15T08:00:00Z", "resolved_at": "2026-07-15T09:30:00Z"},
]}


def fake_rpc(method, params=None):
    if method == "getHealth":
        return "ok"
    if method == "getSlot":
        return 290_123_456
    if method == "getBlockTime":
        return 1_700_600_000
    if method == "getEpochInfo":
        return FAKE_EPOCH_INFO
    if method == "getRecentPerformanceSamples":
        return FAKE_PERF_SAMPLES
    if method == "getVoteAccounts":
        return FAKE_VOTE_ACCOUNTS
    if method == "getSupply":
        return FAKE_SUPPLY
    if method == "getBlock":
        return FAKE_BLOCK
    raise AssertionError(f"unexpected RPC method in smoke test: {method}")


def fake_get_json(url, timeout=None, retries=None):
    if "historicalChainTvl" in url:
        return FAKE_TVL_SERIES
    if "stablecoincharts" in url:
        return FAKE_STABLECOIN_CHART
    if "stablecoinchains" in url:
        return FAKE_STABLECOINS
    if "overview/dexs" in url and "dataType=dailyVolume" in url:
        return FAKE_DEX_VOLUME_CHART
    if "overview/dexs" in url:
        return FAKE_DEX_VOLUME
    if "overview/fees" in url and "excludeTotalDataChart" not in url:
        return FAKE_FEES_CHART
    if "overview/fees" in url:
        return FAKE_FEES
    if "/protocols" in url:
        return FAKE_PROTOCOLS
    if "simple/price" in url:
        return FAKE_COINGECKO_PRICE
    if "days=730" in url:
        return FAKE_COINGECKO_LONG
    if "market_chart" in url:
        return FAKE_COINGECKO_TREND
    if "status.solana.com/api/v2/status.json" in url:
        return FAKE_SOLANA_STATUS
    if "status.solana.com/api/v2/incidents.json" in url:
        return FAKE_SOLANA_INCIDENTS
    if "solana.com" in url:
        from src.http_client import SourceUnavailable
        raise SourceUnavailable("simulated 404 for solana.com/data (expected/handled)")
    if "stakewiz.com" in url:
        return FAKE_STAKEWIZ_VALIDATORS
    raise AssertionError(f"unexpected GET in smoke test: {url}")


def main():
    test_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(test_dir)
    scratch = os.path.join(test_dir, "_scratch")
    if os.path.exists(scratch):
        shutil.rmtree(scratch)
    os.makedirs(scratch)

    # Point outputs at a scratch dir so we don't clobber real data/ during testing
    from src import config as cfg
    cfg.OUTPUT_DIR = os.path.join(scratch, "data")
    cfg.HISTORY_FILE = os.path.join(cfg.OUTPUT_DIR, "history.jsonl")
    cfg.LATEST_JSON = os.path.join(cfg.OUTPUT_DIR, "latest.json")
    cfg.LATEST_MD = os.path.join(cfg.OUTPUT_DIR, "latest.md")
    cfg.DASHBOARD_DIR = os.path.join(scratch, "dashboard")
    cfg.DASHBOARD_DATA_JSON = os.path.join(cfg.DASHBOARD_DIR, "data.json")

    with mock.patch("src.collectors.solana_rpc._rpc", side_effect=fake_rpc), \
         mock.patch("src.http_client.get_json", side_effect=fake_get_json):

        # Seed fake "history" baseline entries with higher avg_tps so the
        # low sample in FAKE_PERF_SAMPLES triggers the TPS-drop anomaly path.
        # Timestamps are relative to real "now" (not a hardcoded old epoch)
        # so they land in the "recent, full resolution" retention tier
        # instead of being pruned as stale by _downsample_history.
        os.makedirs(cfg.OUTPUT_DIR, exist_ok=True)
        now = time.time()
        with open(cfg.HISTORY_FILE, "w") as f:
            for i in range(5):
                f.write(json.dumps({
                    "generated_at_unix": int(now - (5 - i) * 300),
                    "network_performance": {"avg_tps": 4000, "avg_slot_time_ms": 410},
                    "validators": {"delinquent_stake_pct": 1.0},
                    "defi": {"tvl": {"tvl_usd": 4_000_000_000}},
                    "market": {"price": {"price_usd": 190}},
                }) + "\n")

        from src.main import run_once
        payload = run_once()

    report = payload["report"]
    anomalies = payload["anomalies"]

    assert report["network_performance"]["current_tps"] is not None
    assert report["validators"]["active_count"] == 30
    assert report["validators"]["delinquent_count"] == 1
    assert report["defi"]["tvl"]["tvl_usd"] == 4_500_000_000
    assert report["defi"]["top_protocols"]["protocol_count"] == 2  # Aave excluded (no Solana chainTvl), Binance CEX excluded (category)
    assert report["defi"]["top_protocols"]["protocols"][0]["name"] == "Jupiter"
    assert all(p["category"] != "CEX" for p in report["defi"]["top_protocols"]["protocols"])
    categories = report["defi"]["top_protocols"]["categories"]
    assert len(categories) == 2  # "DEX Aggregator" and "Lending" from FAKE_PROTOCOLS (CEX/Ethereum-only excluded)
    assert categories[0]["category"] == "DEX Aggregator"  # Jupiter's 900M > Kamino's 600M
    assert abs(sum(c["pct_of_solana_tvl"] for c in categories) - 100.0) < 0.01
    assert report["validators"]["top_validators"][0]["name"] == "Test Validator Zero"
    assert report["validators"]["top_validators"][0]["website"] == "https://twitter.com/testvalidator0"
    assert "history_series" in payload and len(payload["history_series"]) >= 5
    assert "long_history" in report
    assert len(report["long_history"]["price"]["series"]) == 30
    assert len(report["long_history"]["tvl"]["series"]) == len(FAKE_TVL_SERIES)
    assert len(report["long_history"]["stablecoin_supply"]["series"]) == 2
    assert report["active_wallets_sample"]["unique_wallets_in_block"] == 2
    assert report["active_wallets_sample"]["tx_count_in_block"] == 3
    assert report["solana_network_status"]["current"]["indicator"] == "none"
    assert report["solana_network_status"]["incident_history"]["days_since_last_incident"] is not None
    assert report["solana_network_status"]["incident_history"]["last_incident_name"] == "Elevated skip rate on mainnet-beta"
    assert report["market"]["price"]["price_usd"] == 210.5
    assert any(a["metric"] == "avg_tps" for a in anomalies), "expected a TPS anomaly to fire"
    assert any(a["metric"] == "sol_price_change_pct_24h" for a in anomalies), "expected a price-move anomaly to fire"

    assert os.path.exists(cfg.LATEST_JSON)
    assert os.path.exists(cfg.LATEST_MD)
    assert os.path.exists(cfg.DASHBOARD_DATA_JSON)

    with open(cfg.LATEST_MD) as f:
        md = f.read()
    assert "# Solana Ecosystem Report" in md
    assert "Top 20 Validators" in md or "Top" in md

    print("ALL SMOKE TESTS PASSED")
    print(f"  anomalies detected: {len(anomalies)}")
    for a in anomalies:
        print(f"   - [{a['severity']}] {a['message']}")

    shutil.rmtree(scratch)
    test_downsample_history()


def test_downsample_history():
    """Direct unit test of the tiered history retention logic."""
    from src.assemble import _downsample_history
    now = 1_800_000_000  # arbitrary fixed "now" for deterministic math
    import src.assemble as assemble_mod
    original_time = assemble_mod.time.time
    assemble_mod.time.time = lambda: now

    try:
        entries = []
        # 10 entries in the last 48h, 5 min apart -> all should be kept as-is
        for i in range(10):
            entries.append({"generated_at_unix": now - i * 300})
        # 5 entries scattered within the same hour, 10-40 days old -> only
        # one per hour-bucket should survive. Offset by 30 min off any hour
        # boundary so all 5 land solidly within one bucket regardless of
        # exact alignment.
        for i in range(5):
            entries.append({"generated_at_unix": now - 15 * 86400 - 1800 - i * 60})
        # 3 entries within the same day, ~100 days old -> only one per
        # day-bucket should survive
        for i in range(3):
            entries.append({"generated_at_unix": now - 100 * 86400 - i * 3600})
        # 1 entry way older than the 180-day daily window -> dropped entirely
        entries.append({"generated_at_unix": now - 400 * 86400})

        result = _downsample_history(entries)
        result_timestamps = [e["generated_at_unix"] for e in result]

        assert len(result) == 10 + 1 + 1, f"expected 12 entries after downsampling, got {len(result)}"
        assert (now - 400 * 86400) not in result_timestamps, "entry older than 180 days should have been dropped"
        assert result == sorted(result, key=lambda e: e["generated_at_unix"]), "result should be sorted ascending"

        print("DOWNSAMPLING TEST PASSED")
    finally:
        assemble_mod.time.time = original_time


if __name__ == "__main__":
    main()
