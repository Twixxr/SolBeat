"""
Central configuration for the Solana Ecosystem Report ("SolPulse Canada").

No API keys are required anywhere in this project. All endpoints below are
public, unauthenticated endpoints. If you have a private/paid RPC endpoint
(Helius, Triton, QuickNode, etc.) you can drop it into SOLANA_RPC_URL via
the SOLANA_RPC_URL environment variable for higher rate limits — but the
default public endpoint works fine for a report that refreshes every
15-60 minutes.
"""

import os

# ---------------------------------------------------------------------------
# Solana RPC
# ---------------------------------------------------------------------------
# Public mainnet-beta endpoint. Rate limited (roughly 40 req / 10s / IP) —
# our RPC client below respects that with backoff + small delays between
# calls. Swap in your own RPC URL via env var for heavier use.
SOLANA_RPC_URL = os.environ.get("SOLANA_RPC_URL", "https://api.mainnet-beta.solana.com")

# Number of performance samples to pull for TPS averaging (each sample ~ 60s)
PERFORMANCE_SAMPLE_LIMIT = 30

# How many top validators (by active stake) to include in the report
TOP_VALIDATOR_COUNT = 20

# ---------------------------------------------------------------------------
# Off-chain data sources (no key required)
# ---------------------------------------------------------------------------
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
COINGECKO_MARKET_CHART_URL = (
    "https://api.coingecko.com/api/v3/coins/solana/market_chart"
    "?vs_currency=usd&days=7&interval=daily"
)
# Best-effort ~2 year history for the dashboard's expanded charts. CoinGecko's
# free/public tier has, at times, capped how far back anonymous requests can
# go — if that happens here, this call fails gracefully (see collect_long_history)
# and the dashboard shows "not enough history" for price/market cap/volume
# rather than breaking. See README "Known limitations."
COINGECKO_MARKET_CHART_LONG_URL = (
    "https://api.coingecko.com/api/v3/coins/solana/market_chart"
    "?vs_currency=usd&days=730&interval=daily"
)

# solana.com/data is a client-rendered dashboard (no clean public JSON API).
# We treat it as a "best-effort" source: we try a couple of known underlying
# endpoints, and fall back gracefully (report just omits that field) so the
# whole pipeline never breaks because of one flaky source. See
# src/collectors/solana_data_site.py for details.
SOLANA_DATA_SITE_URL = "https://solana.com/data"

# ---------------------------------------------------------------------------
# HTTP behaviour
# ---------------------------------------------------------------------------
HTTP_TIMEOUT_SECONDS = 15
HTTP_MAX_RETRIES = 3
HTTP_RETRY_BACKOFF_SECONDS = 2.0
USER_AGENT = "SolPulseCanada/1.0 (+https://github.com/YOUR_GITHUB_USERNAME/solpulse-canada)"

# Cap on how many daily points are kept per long-history series (price, TVL,
# stablecoin supply, DEX volume, chain revenue), to keep the JSON payload
# a reasonable size. ~2 years of daily points.
LONG_HISTORY_MAX_POINTS = 730

# ---------------------------------------------------------------------------
# Anomaly detection thresholds
# ---------------------------------------------------------------------------
ANOMALY_THRESHOLDS = {
    # TPS below this vs. the trailing average triggers a "low TPS" flag
    "tps_drop_pct": 25,          # % drop from rolling baseline
    "tps_spike_pct": 60,         # % spike from rolling baseline
    "slot_time_ms_warn": 500,    # average ms/slot above this is slow (target ~400ms)
    "delinquent_stake_pct_warn": 5,   # % of total stake delinquent -> warn
    "delinquent_stake_pct_critical": 10,  # -> critical
    "tvl_change_pct_24h": 10,    # +/- % TVL move in 24h considered notable
    "sol_price_change_pct_24h": 8,  # +/- % price move in 24h considered notable
    "sol_price_change_pct_1h": 3,   # +/- % price move in 1h considered notable
}

# ---------------------------------------------------------------------------
# Automation
# ---------------------------------------------------------------------------
# Default refresh interval when running in continuous/loop mode (minutes).
# Overridden by --interval CLI flag. The GitHub Actions workflow uses its
# own cron schedule instead of this loop (see .github/workflows/update.yml).
DEFAULT_REFRESH_INTERVAL_MINUTES = 30

# Where outputs are written
OUTPUT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
HISTORY_FILE = os.path.join(OUTPUT_DIR, "history.jsonl")  # append-only, used for anomaly baselines
LATEST_JSON = os.path.join(OUTPUT_DIR, "latest.json")
LATEST_MD = os.path.join(OUTPUT_DIR, "latest.md")
DASHBOARD_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "dashboard")
DASHBOARD_HTML = os.path.join(DASHBOARD_DIR, "index.html")
DASHBOARD_DATA_JSON = os.path.join(DASHBOARD_DIR, "data.json")  # what the HTML dashboard fetches client-side

# Max history entries kept in history.jsonl (rolling window so the file
# doesn't grow unbounded in a long-running repo)
MAX_HISTORY_ENTRIES = 2000
