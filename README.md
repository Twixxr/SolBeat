# SolBeat

An automatically updating heartbeat monitor for the Solana ecosystem, built for the Superteam Canada **Solana Ecosystem Report** bounty.

**Live dashboard:** https://twixxr.github.io/SolBeat/

## What this is

SolBeat combines live Solana network, validator, market, DeFi, activity, status, and ecosystem data into an automated report and interactive dashboard. It:

1. Pulls live data from Solana JSON-RPC, DeFiLlama, CoinGecko, Stakewiz, Solana Status, Dune (optional), and public ecosystem sources.
2. Maintains tiered historical data.
3. Runs anomaly detection against thresholds and recent history.
4. Produces a deterministic **Current Solana Outlook** from network health, validators, DeFi, market, activity, and incident status.
5. Writes JSON, Markdown, and dashboard data.
6. Runs automatically through GitHub Actions and deploys to GitHub Pages.

The core pipeline has no required Python third-party packages. Dune and Twitter/X are optional integrations.

## How SolBeat meets the bounty criteria

- **Comprehensiveness:** network performance, validators, stake concentration, SOL economics, stablecoins, DEX volume, fees/revenue, daily active addresses, ecosystem watchlist, network incidents, and upcoming protocol developments.
- **Automation & maintainability:** isolated collectors, graceful source failures, tiered history, anomaly detection, generated reports, and a 5-minute GitHub Actions schedule.
- **Clarity & presentation:** dark interactive dashboard, tabs, expandable history, alerts, plain-English insights, and a landing-page outlook.
- **Innovation:** the report turns raw metrics into a current network outlook and combines live health signals with historical baselines.
- **Technical implementation:** standard-library HTTP collection, modular collectors, retries, generated artifacts, and tests.

## Dashboard

The static dashboard provides:

- **Landing-page Solana Outlook** — a data-driven summary of current network condition, positive signals, and risks to watch.
- **Heartbeat header** with an ECG-style Solana visualization.
- **Hero metrics** for SOL price, network TPS, DeFi TVL, and active validators.
- **Five tabs:** Overview, Network, Onchain DeFi, Validators, and Ecosystem.
- **Daily active addresses** when Dune is configured, with the source clearly labeled.
- **Expandable history charts** for tracked economic and network indicators.
- **TradingView SOL chart** embedded in the SOL price history modal.
- **Anomaly banners** when configured thresholds are triggered.
- **Live relative timestamps** and automatic data polling.

The browser checks dashboard data about every 4 seconds, while the backend normally generates new data every 5 minutes. Browser polling does not call upstream APIs every 4 seconds.

## Data sources

| Source | Main data | Integration |
|---|---|---|
| **Solana JSON-RPC** | Slots, block height, epoch progress, TPS, slot time, validators, stake, commission, delinquency, SOL supply, and a live-block activity sample | Standard-library JSON-RPC calls |
| **DeFiLlama** | Chain TVL, stablecoin supply, DEX volume, fees/revenue, historical series, and protocol TVL | Public keyless REST endpoints |
| **CoinGecko** | SOL price, 24h change, volume, market cap, and price history | Public keyless REST endpoints |
| **Dune** | Daily active addresses | Optional Read-scoped API key; latest result from a public/owned Dune query |
| **Stakewiz** | Validator names and websites | Public validator profile API |
| **Solana Status** | Current network status and incident history | Public Statuspage API |
| **solana.com/data** | Best-effort ecosystem statistics | Candidate public endpoints with graceful failure |
| **Twitter/X** | Ecosystem watchlist and optional recent posts | Curated links by default; optional `snscrape` |
| **TradingView** | Interactive SOL price chart | Public client-side embed |

Collectors are isolated. If a source is unavailable or rate-limited, the affected section is recorded as an error instead of preventing the entire report from being generated.

## Daily active addresses

Solana JSON-RPC can provide activity samples but not a reliable network-wide daily active-address count. SolBeat therefore supports Dune for the bounty's requested daily-active-address metric.

The default integration uses Dune query **6267602**, the public **“SOL - daily active addresses”** query. Dune's latest-result API requires a Read-scoped API key; the key is kept only as a GitHub Actions secret and is never committed to the repository. If Dune is not configured, the report falls back to the clearly labeled single-block RPC activity sample. Dune's API documentation confirms that the latest-result endpoint accepts a query ID and requires a Read-scoped key. 

## Current Solana Outlook

The landing-page outlook is generated automatically every report cycle. It is **not an AI investment prediction** and does not pretend to know the future. It synthesizes measurable signals:

- network operational status and slot time
- validator delinquency
- SOL 24h movement
- DeFi TVL movement
- Dune daily active addresses when available
- anomaly alerts

The result is a simple state such as **Constructive**, **Mixed / constructive**, **Mixed**, or **Cautious**, followed by the strongest positive signals and risks to watch. This makes the landing page useful even for someone who does not want to interpret every chart themselves.

## Automation

`.github/workflows/update.yml` runs on:

- **A 5-minute cron schedule**
- **Manual `workflow_dispatch` runs**
- **Pushes to `main`**

Each run generates fresh data, commits generated files, and deploys `dashboard/` to GitHub Pages.

### Dune configuration

To enable the daily-active-address metric in GitHub Actions:

1. Create a Dune API key with **Read** access.
2. In GitHub, open **Settings → Secrets and variables → Actions**.
3. Add a repository secret named `DUNE_API_KEY`.
4. Optionally add a repository variable named `DUNE_ACTIVE_ADDRESSES_QUERY_ID` if you want to use a different public/owned Dune query. Otherwise SolBeat uses query `6267602`.
5. Run the workflow manually once to populate the metric.

The API key is never stored in source code. Dune recommends keeping API keys secure and not committing them to version control.

## Historical data

| Data age | Resolution |
|---|---|
| Last 48 hours | Every snapshot |
| 48 hours–30 days | Hourly |
| 30–180 days | Daily |
| Older than 180 days | Dropped |

External historical APIs can provide longer history immediately; locally tracked metrics build genuine history as SolBeat runs.

## Onchain DeFi

The Onchain DeFi tab includes chain TVL, TVL changes, stablecoin supply, DEX volume, fees/revenue, protocol-level TVL, and TVL share by project. Centralized exchanges are excluded from the onchain DeFi breakdown.

## Anomaly detection

`src/anomaly.py` checks each snapshot against configured thresholds and recent history, including TPS changes, slow slots, validator delinquency, TVL movements, SOL price movements, and Solana RPC health.

## Setup

### Run once locally

```bash
git clone https://github.com/Twixxr/SolBeat.git
cd SolBeat
python -m src.main
```

The core pipeline requires no `pip install`. It writes `data/latest.json`, `data/latest.md`, `data/history.jsonl`, and `dashboard/data.json`.

### Run continuously

```bash
python -m src.main --loop --interval 5
```

The interval is measured in minutes.

### GitHub Pages

1. Open **Settings → Pages**.
2. Select **GitHub Actions** as the source.
3. Push to `main` or manually run the update workflow.
4. Dashboard: `https://twixxr.github.io/SolBeat/`

### Optional Twitter/X collection

```bash
pip install -r requirements-optional.txt
```

Without it, the curated watchlist remains available but recent post content is not collected automatically.

## Generated files

The workflow generates:

- `dashboard/data.json`
- `data/latest.json`
- `data/latest.md`
- `data/history.jsonl`

## Project structure

```text
SolBeat/
├── src/
│   ├── config.py
│   ├── http_client.py
│   ├── assemble.py
│   ├── assemble_helpers.py
│   ├── anomaly.py
│   ├── main.py
│   ├── collectors/
│   │   ├── solana_rpc.py
│   │   ├── defillama.py
│   │   ├── coingecko.py
│   │   ├── dune.py
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

## Known limitations

- The Dune metric depends on the configured public/owned query remaining available and returning a compatible result shape.
- Without Dune configuration, the fallback activity metric is a single-block fee-payer sample, not daily active users.
- CoinGecko can rate-limit anonymous requests or restrict historical ranges.
- `solana.com/data` is best-effort because it does not expose a stable documented public API for every metric.
- Optional Twitter/X collection depends on an unofficial scraping dependency.
- Public RPC and third-party API rate limits can affect individual collectors.

## License

See the repository for the current project license and contribution information.
