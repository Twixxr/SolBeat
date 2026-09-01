# SolBeat

An automatically updating heartbeat monitor for the Solana ecosystem, built for the Superteam Canada **Solana Ecosystem Report** bounty.

**Live dashboard:** https://twixxr.github.io/SolBeat/

## What this is

SolBeat is a lightweight, no-required-API-key pipeline that collects and presents live Solana ecosystem data. It:

1. Pulls live data from Solana JSON-RPC, DeFiLlama, CoinGecko, Stakewiz, Solana Status, and other public sources.
2. Combines the data into a structured ecosystem report.
3. Maintains tiered historical data so metrics without external history can build a real time series over time.
4. Runs anomaly detection against thresholds and recent history.
5. Writes machine-readable JSON, human-readable Markdown, and dashboard data.
6. Runs automatically through GitHub Actions and deploys the dashboard to GitHub Pages.

The core pipeline uses Python's standard library, so `requirements.txt` contains no required third-party packages. An optional dependency is available for live Twitter/X collection.

## Dashboard

The static dashboard in `dashboard/index.html` provides:

- **Heartbeat header** with an ECG-style Solana mainnet visualization.
- **Hero metrics** for SOL price, network TPS, DeFi TVL, and active validators.
- **Five tabs:** Overview, Network, Onchain DeFi, Validators, and Ecosystem.
- **Expandable history charts** for tracked economic and network indicators.
- **TradingView SOL chart** embedded in the SOL price history modal.
- **Plain-English insights** that summarize important metrics.
- **Live relative timestamps** such as “Updated X ago.”
- **Anomaly banners** that appear only when a threshold is triggered.
- **Automatic data polling** so the dashboard can notice a newly generated dataset without rebuilding the HTML.

The browser checks the dashboard data about every 4 seconds, but the backend normally generates new data every 5 minutes. Browser polling therefore does not mean that upstream APIs are called every 4 seconds.

## Data sources

| Source | Main data | Integration |
|---|---|---|
| **Solana JSON-RPC** | Slots, block height, epoch progress, TPS, slot time, validators, stake, commission, delinquency, SOL supply, and active-wallet sampling | Direct JSON-RPC calls through Python's standard-library `urllib` |
| **DeFiLlama** | Chain TVL, stablecoin supply, DEX volume, fees/revenue, historical series, and protocol TVL | Public keyless REST endpoints |
| **CoinGecko** | SOL price, 24h change, volume, market cap, and price history | Public keyless REST endpoints |
| **Stakewiz** | Validator names and websites | Public validator profile API |
| **Solana Status** | Current network status and incident history | Public Statuspage API |
| **solana.com/data** | Best-effort ecosystem statistics | Candidate public endpoints with graceful failure |
| **Twitter/X** | Ecosystem watchlist and optional recent posts | Curated links by default; optional `snscrape` support |
| **TradingView** | Interactive SOL price chart | Public client-side embed |

Collectors are isolated from one another. If a source is unavailable or rate-limited, the affected section is recorded as an error instead of preventing the entire report from being generated.

## Automation

The workflow at `.github/workflows/update.yml` runs on:

- **A 5-minute cron schedule**
- **Manual `workflow_dispatch` runs**
- **Pushes to `main`**

Each run generates fresh data, commits changed generated files, and deploys the `dashboard/` directory to GitHub Pages.

Five minutes is intentionally conservative because public data providers can rate-limit repeated requests from shared GitHub Actions infrastructure. If CoinGecko or another provider begins returning HTTP 429 responses, increase the workflow interval to `*/15` or `*/30`.

GitHub's scheduled workflows can be delayed during periods of high load. The workflow also supports manual dispatch and push-triggered runs, which are useful for immediate refreshes.

## Historical data

SolBeat uses a tiered retention system for metrics tracked locally:

| Data age | Resolution |
|---|---|
| Last 48 hours | Every snapshot |
| 48 hours–30 days | Hourly |
| 30–180 days | Daily |
| Older than 180 days | Dropped |

Metrics with external historical APIs, such as SOL price and several DeFiLlama metrics, can also receive longer historical series immediately.

This means metrics that only expose a current value through Solana RPC can gradually build their own genuine history instead of relying on fabricated or interpolated values.

## Active wallets

Solana RPC does not provide a simple network-wide daily-active-address metric. SolBeat therefore samples one recent finalized block and counts unique fee-payer addresses in that block.

This is intentionally presented as a **single-block activity sample**, not as the number of daily active Solana users. Tracking the sample over time provides a comparable signal of network activity without pretending it is a full-network daily total.

## Onchain DeFi

The Onchain DeFi tab includes:

- Chain-wide TVL.
- TVL daily percentage change.
- Stablecoin supply.
- DEX volume.
- Fees/revenue data where available.
- Protocol-level TVL breakdown.
- TVL share by project.

Centralized exchanges are excluded from the onchain DeFi breakdown because they are not onchain DeFi protocols.

## Anomaly detection

`src/anomaly.py` checks each new snapshot against configured thresholds and recent history, including:

- TPS drops and spikes.
- Slow slot times.
- Validator delinquency.
- Large TVL movements.
- Large SOL price movements.
- Solana RPC health.

Each anomaly has a severity and human-readable explanation. The same anomaly data powers the dashboard alerts and the Markdown report.

Thresholds are centralized in `config.ANOMALY_THRESHOLDS`.

## Setup

### Run once locally

```bash
git clone https://github.com/Twixxr/SolBeat.git
cd SolBeat
python -m src.main
```

No `pip install` is required for the core pipeline. The command writes:

- `data/latest.json`
- `data/latest.md`
- `data/history.jsonl`
- `dashboard/data.json`

You can open `dashboard/index.html` directly or serve the `dashboard/` directory with a local static-file server.

### Run continuously

```bash
python -m src.main --loop --interval 5
```

The interval is measured in minutes, so the example refreshes every 5 minutes.

### GitHub Pages

1. Use the repository's **Settings → Pages** page.
2. Select **GitHub Actions** as the source.
3. Push to `main` or manually run the `Update Solana Ecosystem Report` workflow.
4. The dashboard will be published at:

   `https://twixxr.github.io/SolBeat/`

No API keys or repository secrets are required by the core pipeline.

### Optional Twitter/X collection

```bash
pip install -r requirements-optional.txt
```

Without the optional package, the curated ecosystem watchlist remains available but recent post content is not collected automatically.

## Generated files and merge conflicts

The following files are generated by the workflow and should normally not be edited manually:

- `dashboard/data.json`
- `data/latest.json`
- `data/latest.md`
- `data/history.jsonl`

`.gitattributes` marks these files with a `merge=theirs` driver so Git can prefer the generated version during a conflict. The custom merge driver still needs to be configured once on a local machine:

```bash
git config merge.theirs.driver "cp -- %B %A"
```

## Project structure

```text
SolBeat/
├── src/
│   ├── config.py
│   ├── http_client.py
│   ├── assemble.py
│   ├── anomaly.py
│   ├── main.py
│   ├── collectors/
│   │   ├── solana_rpc.py
│   │   ├── defillama.py
│   │   ├── coingecko.py
│   │   ├── stakewiz.py
│   │   ├── solana_data_site.py
│   │   ├── solana_status.py
│   │   └── twitter_feed.py
│   └── report/
│       └── build_markdown.py
├── dashboard/
│   ├── index.html
│   └── data.json
├── data/
│   ├── sample/
│   ├── latest.json
│   ├── latest.md
│   └── history.jsonl
├── tests/
│   └── smoke_test.py
├── .github/workflows/update.yml
├── .gitattributes
├── requirements.txt
└── requirements-optional.txt
```

## Sample output

`data/sample/` contains representative JSON, Markdown, and dashboard-data output so the structure can be inspected without making live API requests.

## Known limitations

- Active wallets is a single-block fee-payer sample, not a network-wide daily active-address count.
- Metrics without an external history API need time to build their local history.
- CoinGecko's public service can rate-limit anonymous requests or restrict historical ranges.
- `solana.com/data` does not expose a stable documented public API for every metric, so its collector is best-effort.
- Optional Twitter/X collection depends on an unofficial scraping dependency and may stop working if X changes its frontend.
- Validator identity information depends on the data available from Stakewiz.
- Public RPC and third-party API rate limits can affect individual collectors.

## License

See the repository for the current project license and contribution information.
