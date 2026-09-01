"""Central configuration for the SolBeat Solana Ecosystem Report."""

import os

SOLANA_RPC_URL = os.environ.get("SOLANA_RPC_URL", "https://api.mainnet-beta.solana.com")
PERFORMANCE_SAMPLE_LIMIT = 30
TOP_VALIDATOR_COUNT = 20

DEFILLAMA_CHAIN_TVL_URL = "https://api.llama.fi/v2/historicalChainTvl/Solana"
DEFILLAMA_PROTOCOLS_URL = "https://api.llama.fi/protocols"
DEFILLAMA_STABLECOINS_URL = "https://stablecoins.llama.fi/stablecoinchains"
DEFILLAMA_STABLECOIN_CHART_URL = "https://stablecoins.llama.fi/stablecoincharts/Solana"
DEFILLAMA_DEX_VOLUME_URL = "https://api.llama.fi/overview/dexs/Solana?excludeTotalDataChart=true&excludeTotalDataChartBreakdown=true"
DEFILLAMA_DEX_VOLUME_CHART_URL = "https://api.llama.fi/overview/dexs/Solana?dataType=dailyVolume"
DEFILLAMA_FEES_REV_URL = "https://api.llama.fi/overview/fees/Solana?excludeTotalDataChart=true&excludeTotalDataChartBreakdown=true&dataType=dailyRevenue"
DEFILLAMA_FEES_CHART_URL = "https://api.llama.fi/overview/fees/Solana?dataType=dailyRevenue"

COINGECKO_PRICE_URL = (
    "https://api.coingecko.com/api/v3/simple/price"
    "?ids=solana&vs_currencies=usd&include_24hr_change=true"
    "&include_24hr_vol=true&include_market_cap=true"
)
COINGECKO_MARKET_CHART_URL = "https://api.coingecko.com/api/v3/coins/solana/market_chart?vs_currency=usd&days=7&interval=daily"
COINGECKO_MARKET_CHART_LONG_URL = "https://api.coingecko.com/api/v3/coins/solana/market_chart?vs_currency=usd&days=730&interval=daily"
SOLANA_DATA_SITE_URL = "https://solana.com/data"

# Optional Dune source. Dune's latest-result endpoint requires a Read-scoped
# API key; the key is supplied through the GitHub Actions secret DUNE_API_KEY.
# Query 6267602 is the public "SOL - daily active addresses" query. Replace
# it with another public/owned query via DUNE_ACTIVE_ADDRESSES_QUERY_ID if desired.
DUNE_API_URL = "https://api.dune.com"
DUNE_API_KEY = os.environ.get("DUNE_API_KEY")
DUNE_ACTIVE_ADDRESSES_QUERY_ID = os.environ.get("DUNE_ACTIVE_ADDRESSES_QUERY_ID", "6267602")

HTTP_TIMEOUT_SECONDS = 15
HTTP_MAX_RETRIES = 3
HTTP_RETRY_BACKOFF_SECONDS = 2.0
USER_AGENT = "SolBeat/1.0 (+https://github.com/Twixxr/SolBeat)"
LONG_HISTORY_MAX_POINTS = 730

ANOMALY_THRESHOLDS = {
    "tps_drop_pct": 25,
    "tps_spike_pct": 60,
    "slot_time_ms_warn": 500,
    "delinquent_stake_pct_warn": 5,
    "delinquent_stake_pct_critical": 10,
    "tvl_change_pct_24h": 10,
    "sol_price_change_pct_24h": 8,
    "sol_price_change_pct_1h": 3,
}

DEFAULT_REFRESH_INTERVAL_MINUTES = 5
OUTPUT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
HISTORY_FILE = os.path.join(OUTPUT_DIR, "history.jsonl")
LATEST_JSON = os.path.join(OUTPUT_DIR, "latest.json")
LATEST_MD = os.path.join(OUTPUT_DIR, "latest.md")
DASHBOARD_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "dashboard")
DASHBOARD_HTML = os.path.join(DASHBOARD_DIR, "index.html")
DASHBOARD_DATA_JSON = os.path.join(DASHBOARD_DIR, "data.json")

HISTORY_FULL_RES_SECONDS = 48 * 3600
HISTORY_HOURLY_RES_SECONDS = 30 * 86400
HISTORY_DAILY_RES_SECONDS = 180 * 86400
HISTORY_ABSOLUTE_MAX_ENTRIES = 5000
