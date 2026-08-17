"""Renders the assembled report dict into a human-readable Markdown file."""

import datetime


def _fmt_usd(value):
    if value is None:
        return "N/A"
    try:
        return f"${value:,.0f}"
    except (ValueError, TypeError):
        return str(value)


def _fmt_num(value, decimals=2):
    if value is None:
        return "N/A"
    try:
        return f"{value:,.{decimals}f}"
    except (ValueError, TypeError):
        return str(value)


def _fmt_pct(value):
    if value is None:
        return "N/A"
    sign = "+" if value > 0 else ""
    return f"{sign}{value:.2f}%"


def render(report, anomalies):
    m = report["meta"]
    net = report.get("network_performance", {})
    val = report.get("validators", {})
    supply = report.get("supply", {})
    defi = report.get("defi", {})
    tvl = defi.get("tvl", {})
    stable = defi.get("stablecoins", {})
    dex = defi.get("dex_volume", {})
    fees = defi.get("fees_and_rev", {})
    market = report.get("market", {}).get("price", {})
    social = report.get("social", {})
    upcoming = report.get("upcoming", [])

    lines = []
    lines.append("# Solana Ecosystem Report — SolPulse Canada")
    lines.append("")
    lines.append(f"_Generated: {m['generated_at_utc']} (UTC)_")
    lines.append("")

    # ---- Anomalies up top so they're impossible to miss -------------------
    if anomalies:
        lines.append("## Alerts")
        lines.append("")
        icon = {"critical": "🔴", "warning": "🟠", "info": "🔵"}
        for a in sorted(anomalies, key=lambda x: {"critical": 0, "warning": 1, "info": 2}[x["severity"]]):
            lines.append(f"- {icon.get(a['severity'], '⚪')} **{a['severity'].upper()}** — {a['message']}")
        lines.append("")
    else:
        lines.append("## Alerts")
        lines.append("")
        lines.append("🟢 No anomalies detected in this snapshot.")
        lines.append("")

    # ---- Network performance -----------------------------------------------
    lines.append("## Network Performance")
    lines.append("")
    lines.append("| Metric | Value |")
    lines.append("|---|---|")
    lines.append(f"| RPC health | {net.get('health', 'N/A')} |")
    lines.append(f"| Current slot | {_fmt_num(net.get('current_slot'), 0)} |")
    lines.append(f"| Block height | {_fmt_num(net.get('block_height'), 0)} |")
    lines.append(f"| Epoch | {net.get('epoch', 'N/A')} |")
    lines.append(f"| Epoch progress | {_fmt_pct(net.get('epoch_progress_pct')).replace('+','')} |")
    lines.append(f"| Current TPS | {_fmt_num(net.get('current_tps'))} |")
    lines.append(f"| Avg TPS (~{net.get('samples_used','?')} samples) | {_fmt_num(net.get('avg_tps'))} |")
    lines.append(f"| Max / Min TPS | {_fmt_num(net.get('max_tps'))} / {_fmt_num(net.get('min_tps'))} |")
    lines.append(f"| Avg slot time | {_fmt_num(net.get('avg_slot_time_ms'), 1)} ms |")
    lines.append("")

    # ---- Validators ----------------------------------------------------------
    lines.append("## Validator Status")
    lines.append("")
    lines.append("| Metric | Value |")
    lines.append("|---|---|")
    lines.append(f"| Active validators | {_fmt_num(val.get('active_count'), 0)} |")
    lines.append(f"| Delinquent validators | {_fmt_num(val.get('delinquent_count'), 0)} |")
    lines.append(f"| Delinquent (% of validator count) | {_fmt_pct(val.get('delinquent_pct_of_validators')).replace('+','')} |")
    lines.append(f"| Delinquent (% of active stake) | {_fmt_pct(val.get('delinquent_stake_pct')).replace('+','')} |")
    lines.append(f"| Total active stake | {_fmt_num(val.get('total_active_stake_sol'), 0)} SOL |")
    conc = val.get("stake_concentration") or {}
    lines.append(f"| Validators controlling 33% of stake | {conc.get('validators_to_control_33pct', 'N/A')} |")
    lines.append("")

    top_validators = val.get("top_validators", [])
    if top_validators:
        lines.append(f"### Top {len(top_validators)} Validators by Stake")
        lines.append("")
        lines.append("| # | Vote Account | Stake (SOL) | Commission | Last Vote |")
        lines.append("|---|---|---|---|---|")
        for i, v in enumerate(top_validators, start=1):
            lines.append(
                f"| {i} | `{v.get('vote_pubkey')}` | {_fmt_num(v.get('activated_stake_sol'), 0)} "
                f"| {v.get('commission_pct')}% | {v.get('last_vote')} |"
            )
        lines.append("")

    # ---- Supply -----------------------------------------------------------
    lines.append("## SOL Supply")
    lines.append("")
    lines.append(f"- Total: {_fmt_num(supply.get('total_sol'), 0)} SOL")
    lines.append(f"- Circulating: {_fmt_num(supply.get('circulating_sol'), 0)} SOL")
    lines.append(f"- Non-circulating: {_fmt_num(supply.get('non_circulating_sol'), 0)} SOL")
    lines.append("")

    # ---- Economic indicators ------------------------------------------------
    lines.append("## Economic Indicators")
    lines.append("")
    lines.append("| Metric | Value |")
    lines.append("|---|---|")
    lines.append(f"| SOL price | {_fmt_usd(market.get('price_usd'))} |")
    lines.append(f"| SOL 24h change | {_fmt_pct(market.get('price_change_pct_24h'))} |")
    lines.append(f"| SOL 24h volume | {_fmt_usd(market.get('volume_24h_usd'))} |")
    lines.append(f"| SOL market cap | {_fmt_usd(market.get('market_cap_usd'))} |")
    lines.append(f"| Solana chain TVL | {_fmt_usd(tvl.get('tvl_usd'))} |")
    lines.append(f"| TVL change (24h) | {_fmt_pct(tvl.get('tvl_change_pct_24h'))} |")
    lines.append(f"| TVL change (7d) | {_fmt_pct(tvl.get('tvl_change_pct_7d'))} |")
    lines.append(f"| Stablecoin supply on Solana | {_fmt_usd(stable.get('total_stablecoin_supply_usd'))} |")
    lines.append(f"| DEX volume (24h) | {_fmt_usd(dex.get('dex_volume_24h_usd'))} |")
    lines.append(f"| Chain revenue / REV proxy (24h) | {_fmt_usd(fees.get('chain_revenue_24h_usd'))} |")
    lines.append("")

    top_dexs = dex.get("top_dexs_by_volume", [])
    if top_dexs:
        lines.append("### Top DEXs by 24h Volume")
        lines.append("")
        lines.append("| DEX | 24h Volume |")
        lines.append("|---|---|")
        for d in top_dexs:
            lines.append(f"| {d.get('name')} | {_fmt_usd(d.get('volume_24h_usd'))} |")
        lines.append("")

    # ---- Ecosystem / community news -----------------------------------------
    lines.append("## Ecosystem & Community Watchlist")
    lines.append("")
    if social.get("_note"):
        lines.append(f"_{social['_note']}_")
        lines.append("")
    for acc in social.get("accounts", []):
        lines.append(f"- **{acc['handle']}** — {acc['reason']}")
        for t in acc.get("recent_tweets", [])[:3]:
            lines.append(f"  - {t.get('date', '')}: {t.get('content', '')[:200]} ({t.get('url', '')})")
    lines.append("")

    # ---- Upcoming ------------------------------------------------------------
    lines.append("## Upcoming Upgrades & Developments")
    lines.append("")
    for u in upcoming:
        lines.append(f"- **{u['name']}** — {u['description']} ([track]({u['track']}))")
    lines.append("")

    # ---- Footer --------------------------------------------------------------
    lines.append("---")
    lines.append("")
    lines.append(
        "_This report is generated automatically from public, keyless data "
        "sources (Solana RPC, DeFiLlama, CoinGecko). See README.md for the "
        "full source list, automation strategy, and how to run this "
        "yourself._"
    )
    lines.append("")

    return "\n".join(lines)
