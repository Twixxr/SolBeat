# SolBeat

An automatically-updating heartbeat monitor for the Solana ecosystem — built for the Superteam Canada "Solana Ecosystem Report" bounty.

**Live dashboard:** `https://YOUR_GITHUB_USERNAME.github.io/YOUR_REPO_NAME/` (enable GitHub Pages, see [Setup](#setup))
**Sample outputs:** [`data/sample/`](data/sample/) — a full JSON, Markdown, and dashboard-data sample generated from the pipeline, so you can see the shape of the real output without running anything.

---

## What this is

A no-API-key, low-dependency pipeline that:

1. Pulls live data directly from **Solana RPC**, **DeFiLlama**, **CoinGecko**, and **Stakewiz**.
2. Assembles it into one structured report, with a **tiered history system** that keeps genuine long-term data for every metric — not just the ones with an external historical API.
3. Runs a lightweight **anomaly detector** against rolling history.
4. Writes three output formats: `data/latest.json` (machine-readable), `data/latest.md` (human-readable), and `dashboard/data.json` (feeds the dark-theme HTML dashboard).
5. Repeats automatically on a schedule via **GitHub Actions**, committing fresh data and redeploying the dashboard to **GitHub Pages** — no server to run or maintain.

Every requirement in the bounty's "No API Keys/Dependencies" preference is honored: the entire data-collection path runs on Python's standard library (`urllib`) with zero required third-party packages. `requirements.txt` is intentionally empty for that reason.

### The dashboard

`dashboard/index.html` is a tabbed, chart-driven interface with a few things worth calling out:

- **Heartbeat monitor header** — an actual ECG-style trace draws itself left to right, then fades and repeats, styled like real patient-monitor hardware (grid background, glow, monospace readout). Data refreshes every time it completes a loop.
- **Hero strip** — SOL price, network TPS, onchain DeFi TVL, and active validator count stay visible above the tabs at all times.
- **Insight sentences** — a couple of sections open with a plain-English sentence synthesizing the numbers below it (e.g. "SOL is trading at $210, up 3.2% over the last 24 hours..."), rather than leaving raw numbers to interpret cold.
- **Five tabs**: Overview, Network, Onchain DeFi, Validators, Ecosystem.
- **Click-to-expand history** — every economic indicator card opens a large modal chart on click. The SOL Price card's modal is a real embedded **TradingView** widget (plain iframe embed) instead of a custom chart. Other cards use the project's own tracked history.
- **Live-feeling but honest about cadence** — the browser re-checks `data.json` every heartbeat loop (~4s) with a cache-busting parameter to defeat GitHub Pages' CDN caching, but only re-renders when the data is actually new (the backend itself updates on whatever schedule `.github/workflows/update.yml` runs, default every 5 minutes) — so it never flickers on every check.
- **"Updated X ago"** ticks live in the header instead of a static timestamp.
- Anomaly banners only appear when there's an actual anomaly — no permanent "all clear" clutter.

---

## Data sources & how they're integrated

| Source | What it provides | How |
|---|---|---|
| **Solana JSON-RPC** (`api.mainnet-beta.solana.com`) | Slot, block height, epoch progress, TPS, slot time, validator set, stake distribution, commission, delinquency, SOL supply, active-wallet sampling | Direct JSON-RPC POST calls via stdlib `urllib` — `getHealth`, `getSlot`, `getBlockTime`, `getEpochInfo`, `getRecentPerformanceSamples`, `getVoteAccounts`, `getSupply`, `getBlock`, plus `getBalance`/`getSignaturesForAddress` exposed as reusable helpers. See [`src/collectors/solana_rpc.py`](src/collectors/solana_rpc.py). |
| **DeFiLlama** | Chain TVL (+24h/7d change, full history, daily % change chart), stablecoin supply (+full history), DEX volume (+full history), chain fees/revenue (REV proxy, +full history), per-protocol TVL breakdown | Public, keyless REST endpoints (`api.llama.fi`, `stablecoins.llama.fi`). See [`src/collectors/defillama.py`](src/collectors/defillama.py). |
| **CoinGecko** | SOL price, 24h change, volume, market cap, ~2-year daily history | Public `simple/price` and `market_chart` endpoints, no key required. See [`src/collectors/coingecko.py`](src/collectors/coingecko.py). |
| **Stakewiz** | Validator operator identity (name, website) | Free, keyless API aggregating validator-submitted off-chain profile info. See [`src/collectors/stakewiz.py`](src/collectors/stakewiz.py) and Known limitations below. |
| **solana.com/data** | Best-effort ecosystem stats | That page has no documented public JSON API (it's client-rendered). Rather than bolt on a fragile/heavy headless-browser dependency, this collector tries a couple of known candidate endpoints and degrades gracefully if they're unavailable. See [`src/collectors/solana_data_site.py`](src/collectors/solana_data_site.py). |
| **Twitter / X** | Ecosystem announcements & sentiment sources | X's official API requires a paid tier, which conflicts with "no API keys." A curated watchlist of high-signal accounts is always included, each with a direct clickable link. If the optional `snscrape` package is installed, the collector live-pulls recent tweets too. See [`src/collectors/twitter_feed.py`](src/collectors/twitter_feed.py). |
| **Solana Status** (status.solana.com) | Real Solana network status and days-since-last-incident | Free, keyless public API (Atlassian Statuspage's standard `/api/v2/status.json` and `/api/v2/incidents.json` endpoints) — verified against the real live response before building against it. See `src/collectors/solana_status.py`. |
| **TradingView** | Interactive SOL price chart | Free public embed widget (client-side script, no key), shown inside the SOL Price card's expand modal. |
| **Upcoming upgrades** (Alpenglow, SIMD proposals, Firedancer) | Slow-moving roadmap items | Curated, linked list in [`src/assemble.py`](src/assemble.py) — manually maintained since these move on a months-long cadence with no single stable feed. |

Every collector wraps its HTTP calls in retries with backoff (see [`src/http_client.py`](src/http_client.py)) and fails independently — if one source is rate-limited or down, the rest of the report still generates normally, with the affected section marked `_errors` instead of crashing the whole run.

---

## Automation strategy

1. **GitHub Actions** ([`.github/workflows/update.yml`](.github/workflows/update.yml)) — runs on a cron schedule (default: every 5 minutes), regenerates the report, commits the updated `data/*` and `dashboard/data.json` files back to the repo, and redeploys the dashboard to GitHub Pages. Zero servers, fully hosted, free on a public repo.
2. **Local loop mode** — `python -m src.main --loop --interval 5` runs the same pipeline continuously on your own machine, a cron job, a systemd timer, or a container, if you'd rather not use GitHub Actions.

The dashboard itself is a static file that fetches `data.json` client-side — redeploying the HTML isn't needed between data refreshes, only `dashboard/data.json` needs to update, which the Action does automatically.

**On refresh frequency:** 5 minutes is close to the edge of what CoinGecko's free tier comfortably tolerates from a shared GitHub Actions IP pool. If you see `429` errors in the Action logs, loosen the cron schedule back toward `*/15` or `*/30` in `.github/workflows/update.yml` — there's a comment right above the schedule line explaining this.

**On GitHub's scheduler reliability:** GitHub's own `schedule:` cron trigger is documented to be unreliable on public repos with light traffic — it can be delayed by hours or silently dropped entirely, even with a perfectly valid workflow file. `push` and manual (`workflow_dispatch`) triggers don't have this problem, since they're event-driven rather than polled. If your Action only seems to run when you push code or trigger it manually — never on its own — this is almost certainly why.

The reliable fix: use a free external scheduler (e.g. [cron-job.org](https://cron-job.org)) to call GitHub's REST API on a real clock, sidestepping GitHub's internal scheduler entirely:

1. Create a GitHub fine-grained personal access token (Settings → Developer settings → Personal access tokens → Fine-grained tokens), scoped to only this repository, with **Actions: Read and write** permission and nothing else.
2. Set up a free cron job at a service like cron-job.org that sends a `POST` request every 5 minutes to:
   `https://api.github.com/repos/YOUR_GITHUB_USERNAME/YOUR_REPO_NAME/actions/workflows/update.yml/dispatches`
   with headers `Authorization: Bearer YOUR_TOKEN`, `Accept: application/vnd.github+json`, `Content-Type: application/json`, and body `{"ref":"main"}`.

This calls GitHub's `workflow_dispatch` API on a genuinely reliable external clock, which then triggers the same workflow as a normal manual run.

---

## Historical data — how "everything" gets real history

Rather than only tracking history for metrics with an external historical API (price, TVL, etc.), this project keeps genuine long-term history for every metric — including the ones Solana RPC only reports the current value for (TPS, slot time, validator count, SOL supply, active-wallet sample) — using a tiered retention system in [`src/assemble.py`](src/assemble.py):

| Age of data point | Resolution kept |
|---|---|
| Last 48 hours | Every snapshot (full resolution) |
| 48 hours – 30 days | One per hour |
| 30 – 180 days | One per day |
| Older than 180 days | Dropped |

This keeps `data/history.jsonl` bounded to a few thousand lines forever, regardless of how often the Action runs, while still building toward a genuine 6-month picture for metrics that have no other source of history. It's covered by a dedicated unit test in [`tests/smoke_test.py`](tests/smoke_test.py).

Metrics with a real external historical API (SOL price, market cap, volume via CoinGecko; chain TVL, stablecoin supply, DEX volume, chain revenue via DeFiLlama) additionally get ~2 years of real daily history pulled fresh each run — no waiting for this project's own tracking to catch up. The dashboard's history modal states which kind of history you're looking at for any given card.

---

## Active wallets — how it actually works

Solana's live RPC has no "daily active addresses" endpoint, and building a true one requires a paid indexer (Dune, Flipside, Artemis), which conflicts with this bounty's "no API keys" preference. Instead of skipping the metric entirely, this project computes something real: it samples one recent finalized block via `getBlock` and counts the unique fee-payer addresses within it.

This is honestly labeled as exactly what it is — a live, real, RPC-computed count of wallets seen in one sampled block, **not** a network-wide daily total. Tracked over time (via the tiered history system above), it still gives a genuine, comparable signal of relative network activity, computed directly from chain data rather than estimated or faked.


---


## Onchain DeFi

The Onchain DeFi tab shows chain-wide metrics (including a **TVL daily % change** chart, computed from DeFiLlama's daily TVL history), a **day-over-day % change bar chart** for TVL, and per-project TVL breakdown (table + % share chart). CEXs are excluded throughout, since they aren't onchain DeFi.

## Anomaly detection

Implemented in [`src/anomaly.py`](src/anomaly.py), each run checks the new snapshot against fixed thresholds and a rolling baseline from recent history:

- **TPS drop/spike** — vs. the trailing average of recent snapshots (±25% drop = warning, +60% spike = info).
- **Slow slot times** — average ms/slot above 500ms (target ~400ms).
- **Validator delinquency** — % of active stake delinquent, with warning (5%) and critical (10%) thresholds.
- **TVL moves** — ±10%+ swing in chain TVL over 24h.
- **SOL price moves** — ±8%+ swing over 24h.
- **RPC health** — flags immediately (critical) if `getHealth` doesn't return `"ok"`.

Each anomaly carries a severity, a human-readable message, and the raw value/baseline, driving both the dashboard's alert banners (which only appear when something is actually flagged) and the Markdown report's "Alerts" section. Thresholds live in one place: `config.ANOMALY_THRESHOLDS`.

---

## Setup

### Run it once, locally

```bash
git clone https://github.com/YOUR_GITHUB_USERNAME/YOUR_REPO_NAME.git
cd YOUR_REPO_NAME
python -m src.main
```

No `pip install` required for the core report. This writes `data/latest.json`, `data/latest.md`, `data/history.jsonl`, and `dashboard/data.json`. Open `dashboard/index.html` directly in a browser (or serve the `dashboard/` folder with any static file server) to view it against your freshly generated data.

### Run it continuously, locally

```bash
python -m src.main --loop --interval 5   # refresh every 5 minutes
```

### Host it automatically (recommended)

1. Fork/clone this repo to your own GitHub account.
2. In your repo settings → Pages, set the source to GitHub Actions.
3. Push to `main` — the included workflow runs immediately (and on its cron schedule after), commits fresh data, and deploys the dashboard.
4. Your live dashboard will be at `https://YOUR_GITHUB_USERNAME.github.io/YOUR_REPO_NAME/`.

No secrets or API keys need to be configured.

### Avoiding merge conflicts on generated files

`dashboard/data.json`, `data/latest.json`, `data/latest.md`, and `data/history.jsonl` are regenerated automatically by the Action. If you also edit files locally and push, git can ask you to manually resolve a "conflict" on these — even though there's nothing to decide, since they're always supposed to just reflect whatever the bot last generated.

Run this once, locally, to make git auto-resolve those files by always keeping the bot's version:

```bash
git config merge.theirs.driver "cp -- %B %A"
```

This works with the `.gitattributes` file already in this repo. After running it once, `git pull` silently keeps the bot's version of those files on conflict, so you'll only ever need to resolve real conflicts in files you actually edited.

### Optional: live Twitter/X pulling

```bash
pip install -r requirements-optional.txt
```

Without this, the ecosystem watchlist still lists the curated accounts to check manually — the report just won't embed live tweet content.

### Dependencies

- Required: none beyond the Python standard library (3.9+).
- Optional: `snscrape`, only for live Twitter/X pulling.

---

## Project structure

```
solbeat/
├── src/
│   ├── config.py              # all endpoints, thresholds, retention tiers, paths
│   ├── http_client.py         # stdlib urllib wrapper w/ retries + backoff
│   ├── assemble.py            # pulls all collectors together, tiered history retention
│   ├── anomaly.py             # threshold + rolling-baseline anomaly detection
│   ├── main.py                # CLI entrypoint (single run or --loop)
│   ├── collectors/
│   │   ├── solana_rpc.py      # network perf, validators, supply, active-wallet sampling
│   │   ├── defillama.py       # TVL, stablecoins, DEX volume, fees/REV + long history
│   │   ├── coingecko.py       # SOL price, market cap, volume + ~2yr history
│   │   ├── stakewiz.py        # validator name/website enrichment
│   │   ├── solana_data_site.py# best-effort solana.com/data
│   │   └── twitter_feed.py    # curated watchlist + optional live pulling
│   └── report/
│       └── build_markdown.py  # renders report dict -> Markdown
├── dashboard/
│   ├── index.html             # dark-theme dashboard: heartbeat header, tabs, modals, charts
│   └── data.json              # generated output the dashboard reads
├── data/
│   ├── sample/                # sample JSON/MD/dashboard-data outputs
│   ├── latest.json            # generated on run
│   ├── latest.md              # generated on run
│   └── history.jsonl          # generated/appended on run, tiered retention applied
├── tests/
│   └── smoke_test.py          # offline test w/ mocked network calls + downsampling unit test
├── .github/workflows/update.yml
├── .gitattributes
├── requirements.txt
└── requirements-optional.txt
```

## Sample outputs

`data/sample/` contains a full sample run so reviewers can see exact output shape without running the pipeline. These were generated from mocked data to validate the pipeline structure, not a live network pull — run `python -m src.main` yourself for a real snapshot (see `tests/smoke_test.py` for how the mock harness works, which doubles as a lightweight test suite).

## Known limitations

- "Active wallets" is a single-block sample, not a network total — see the section above. This is a deliberate, honestly-labeled design choice, not an oversight.
- History depth varies by metric's data source, not arbitrarily. Metrics with an external historical API (price, TVL, stablecoin supply, DEX volume, chain revenue, market cap) get ~2 years immediately. Metrics with no such source (TPS, slot time, validator count, SOL supply, active wallets) build up to 6 months over time via this project's own tiered retention.
- CoinGecko's public tier has, at times, capped how far back anonymous requests can go (historically up to ~365 days); this project requests ~2 years and degrades gracefully (shows "not enough history") if that range isn't honored when you run it.
- solana.com/data has no stable public API — covered best-effort only.
- Twitter/X live content requires the optional `snscrape` dependency and can break if X changes their frontend; the curated watchlist with direct links is always present as a fallback.
- "TVL split by coin" isn't offered — DeFiLlama has no keyless "TVL by underlying token across a chain" endpoint (it would require one call per protocol). The Onchain DeFi tab shows % share of TVL by project instead (CEXs excluded), which is more directly useful anyway.
- Validator identity (name/website) comes from Stakewiz, which has no dedicated Twitter/X field — the dashboard's 𝕏 badge links to a validator's website when that URL happens to be a twitter.com/x.com link, otherwise it's a plain website link (🔗). Not every operator publishes either, so unmatched validators show as "Unknown" rather than a raw address.
- Solana network uptime/incident history is sourced live from status.solana.com's official public API (shown as "Solana Network Status" and "Days Since Last Incident" on the Overview tab) -- a real, keyless, official source.
- Public RPC/CoinGecko rate limits — see Automation strategy above.
