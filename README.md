# SolPulse Canada

An automatically-updating report on the current state of the Solana ecosystem — built for the Superteam Canada "Solana Ecosystem Report" bounty.

**Live dashboard:** `https://YOUR_GITHUB_USERNAME.github.io/solpulse-canada/` (enable GitHub Pages, see [Setup](#setup))
**Sample outputs:** [`data/sample/`](data/sample/) — a full JSON, Markdown, and dashboard-data sample generated from the pipeline, so you can see the shape of the real output without running anything.

---

## What this is

A no-API-key, low-dependency pipeline that:

1. Pulls live data directly from **Solana RPC**, **DeFiLlama**, and **CoinGecko**.
2. Assembles it into one structured report.
3. Runs a lightweight **anomaly detector** against rolling history.
4. Writes three output formats: `data/latest.json` (machine-readable), `data/latest.md` (human-readable), and `dashboard/data.json` (feeds the dark-theme HTML dashboard).
5. Repeats automatically on a schedule via **GitHub Actions**, committing fresh data and redeploying the dashboard to **GitHub Pages** — no server to run or maintain.

Every requirement in the bounty's "No API Keys/Dependencies" preference is honored: the entire data-collection path (RPC + DeFiLlama + CoinGecko) runs on Python's standard library (`urllib`) with zero required third-party packages. `requirements.txt` is intentionally empty for that reason.

---

## Data sources & how they're integrated

| Source | What it provides | How |
|---|---|---|
| **Solana JSON-RPC** (`api.mainnet-beta.solana.com`) | Slot, block height, epoch progress, TPS, slot time, validator set, stake distribution, commission, delinquency, SOL supply | Direct JSON-RPC POST calls via stdlib `urllib` — `getHealth`, `getSlot`, `getBlockTime`, `getEpochInfo`, `getRecentPerformanceSamples`, `getVoteAccounts`, `getSupply`, plus `getBalance`/`getSignaturesForAddress` exposed as reusable helpers. See [`src/collectors/solana_rpc.py`](src/collectors/solana_rpc.py). |
| **DeFiLlama** | Chain TVL (+24h/7d change), stablecoin supply on Solana, DEX volume, chain fees/revenue (REV proxy) | Public, keyless REST endpoints (`api.llama.fi`, `stablecoins.llama.fi`). See [`src/collectors/defillama.py`](src/collectors/defillama.py). |
| **CoinGecko** | SOL price, 24h change, volume, market cap, 7-day trend | Public `simple/price` and `market_chart` endpoints, no key required. See [`src/collectors/coingecko.py`](src/collectors/coingecko.py). |
| **solana.com/data** | Best-effort ecosystem stats | That page has no documented public JSON API (it's client-rendered). Rather than bolt on a fragile/heavy headless-browser dependency, this collector tries a couple of known candidate endpoints and **degrades gracefully** if they're unavailable, logging a note instead of breaking the pipeline. See [`src/collectors/solana_data_site.py`](src/collectors/solana_data_site.py) for the documented extension point if you want to add Playwright-based scraping. |
| **Twitter / X** | Ecosystem announcements & sentiment sources | X's official API requires a paid tier, which conflicts with "no API keys." Instead, a curated watchlist of high-signal accounts (`@solana`, `@heliuslabs`, `@SuperteamCA`, `@jup_ag`, etc.) is always included. If the *optional* `snscrape` package is installed, the collector live-pulls recent tweets from each account with no key required; otherwise it falls back to just the watchlist with an explanatory note. See [`src/collectors/twitter_feed.py`](src/collectors/twitter_feed.py) and `requirements-optional.txt`. |
| **Upcoming upgrades** (Alpenglow, SIMD proposals, Firedancer) | Slow-moving roadmap items | Maintained as a short, curated, linked list in [`src/assemble.py`](src/assemble.py) — the one manually-updated section, since these move on a months-long cadence and there's no single stable feed for "current SIMD status." |

Every collector wraps its HTTP calls in retries with backoff (see [`src/http_client.py`](src/http_client.py)) and **fails independently** — if CoinGecko is rate-limited, the rest of the report (RPC, DeFiLlama, etc.) still generates normally, with the affected section marked `_errors` instead of crashing the whole run.

---

## Automation strategy

Automation is handled two ways:

1. **GitHub Actions** ([`.github/workflows/update.yml`](.github/workflows/update.yml)) — runs on a cron schedule (default: every 30 minutes), regenerates the report, commits the updated `data/*` and `dashboard/data.json` files back to the repo, and redeploys the dashboard to GitHub Pages. This is the recommended path: zero servers, fully hosted, free on a public repo, and the commit history in `data/history.jsonl` doubles as an audit trail of every snapshot ever taken.
2. **Local loop mode** — `python -m src.main --loop --interval 15` runs the same pipeline continuously on your own machine or a cron job / systemd timer / Docker container, if you'd rather not use GitHub Actions.

The refresh interval is configurable in both paths (the cron expression in the workflow file, or `--interval` / `config.DEFAULT_REFRESH_INTERVAL_MINUTES` for the CLI).

The dashboard itself (`dashboard/index.html`) is a static file that fetches `data.json` client-side on every page load — so redeploying it isn't even necessary between data refreshes once GitHub Pages is serving the folder; only `dashboard/data.json` needs to update, which the Action does automatically.

---

## Anomaly detection

Implemented in [`src/anomaly.py`](src/anomaly.py), each report run checks the new snapshot against both fixed thresholds and a rolling baseline built from `data/history.jsonl` (the last 20 snapshots):

- **TPS drop/spike** — current average TPS vs. the trailing average of recent snapshots (default: ±25% drop = warning, +60% spike = info).
- **Slow slot times** — average ms/slot above 500ms (target is ~400ms).
- **Validator delinquency** — % of active stake that's delinquent, with separate warning (5%) and critical (10%) thresholds.
- **TVL moves** — ±10%+ swing in Solana chain TVL over 24h.
- **SOL price moves** — ±8%+ swing over 24h.
- **RPC health** — flags immediately (critical) if the node's own `getHealth` check doesn't return `"ok"`.

Each anomaly carries a `severity` (`info` / `warning` / `critical`), a human-readable `message`, and the raw `value`/`baseline` numbers, so the same anomaly list drives the red/orange/blue alert banners in the HTML dashboard *and* the "Alerts" section at the top of the Markdown report — one detection pass, three consistent outputs. Thresholds are all in one place ([`config.ANOMALY_THRESHOLDS`](src/config.py)) if you want to tune sensitivity.

---

## Setup

### Run it once, locally

```bash
git clone https://github.com/YOUR_GITHUB_USERNAME/solpulse-canada.git
cd solpulse-canada
python -m src.main
```

That's it — no `pip install` required for the core report (see [Dependencies](#dependencies) below). This writes:

- `data/latest.json`
- `data/latest.md`
- `data/history.jsonl` (appended to, used for anomaly baselines)
- `dashboard/data.json`

Open `dashboard/index.html` directly in a browser (or serve the `dashboard/` folder with any static file server) to view the live dashboard against your freshly generated data.

### Run it continuously, locally

```bash
python -m src.main --loop --interval 15   # refresh every 15 minutes
```

### Host it automatically (recommended)

1. Fork/clone this repo to your own GitHub account.
2. In your repo settings → **Pages**, set the source to **GitHub Actions**.
3. Push to `main` — the included workflow ([`.github/workflows/update.yml`](.github/workflows/update.yml)) will run immediately (and every 30 minutes after), commit fresh data, and deploy the dashboard.
4. Your live dashboard will be at `https://YOUR_GITHUB_USERNAME.github.io/REPO_NAME/`.

No secrets or API keys need to be configured for this to work.

### Optional: live Twitter/X pulling

```bash
pip install -r requirements-optional.txt
```

Without this, the ecosystem watchlist section still lists the curated high-signal accounts to check manually — the report just won't embed live tweet content.

### Dependencies

- **Required:** none beyond the Python standard library (3.9+). `requirements.txt` documents this explicitly.
- **Optional:** `snscrape`, only for live Twitter/X pulling (`requirements-optional.txt`).

---

## Project structure

```
solpulse-canada/
├── src/
│   ├── config.py              # all endpoints, thresholds, paths in one place
│   ├── http_client.py         # stdlib urllib wrapper w/ retries + backoff
│   ├── assemble.py            # pulls all collectors into one report dict
│   ├── anomaly.py             # threshold + rolling-baseline anomaly detection
│   ├── main.py                # CLI entrypoint (single run or --loop)
│   ├── collectors/
│   │   ├── solana_rpc.py      # network perf, validators, supply
│   │   ├── defillama.py       # TVL, stablecoins, DEX volume, fees/REV
│   │   ├── coingecko.py       # SOL price + 7d trend
│   │   ├── solana_data_site.py# best-effort solana.com/data
│   │   └── twitter_feed.py    # curated watchlist + optional live pulling
│   └── report/
│       └── build_markdown.py  # renders report dict -> Markdown
├── dashboard/
│   ├── index.html             # dark-theme interactive dashboard (fetches data.json)
│   └── data.json              # generated output the dashboard reads (seeded w/ sample data)
├── data/
│   ├── sample/                # sample JSON/MD/dashboard-data outputs (see below)
│   ├── latest.json            # generated on run
│   ├── latest.md              # generated on run
│   └── history.jsonl          # generated/appended on run
├── tests/
│   └── smoke_test.py          # offline test w/ mocked network calls
├── .github/workflows/update.yml
├── requirements.txt
└── requirements-optional.txt
```

## Sample outputs

[`data/sample/`](data/sample/) contains a full sample run (`sample-report.json`, `sample-report.md`, `sample-dashboard-data.json`) so reviewers can see exact output shape without running the pipeline. **These were generated from mocked data to validate the pipeline structure**, not a live network pull — run `python -m src.main` yourself for a real snapshot (see [`tests/smoke_test.py`](tests/smoke_test.py) for how the mock harness works, which doubles as a lightweight test suite).

## Known limitations

- **solana.com/data** has no stable public API — covered on a best-effort basis (see table above).
- **Twitter/X live content** requires the optional `snscrape` dependency and can break if X changes their frontend; the curated watchlist is always present as a fallback.
- **Public RPC/CoinGecko rate limits** — the default 30-minute refresh interval comfortably respects free-tier limits; if you tighten it significantly, consider pointing `SOLANA_RPC_URL` at a private RPC provider (env var, still no code changes needed).
