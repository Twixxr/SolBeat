"""Render the assembled report into human-readable Markdown."""


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
    activity = report.get("daily_active_addresses", {})
    outlook = report.get("outlook", {})

    lines = ["# Solana Ecosystem Report — SolBeat", "", f"_Generated: {m['generated_at_utc']} (UTC)_", ""]

    if outlook:
        lines += ["## Current Solana Outlook", "", f"**{outlook.get('rating', 'N/A')}** — {outlook.get('summary', '')}", ""]

    if anomalies:
        lines += ["## Alerts", ""]
        icon = {"critical": "🔴", "warning": "🟠", "info": "🔵"}
        for a in sorted(anomalies, key=lambda x: {"critical": 0, "warning": 1, "info": 2}[x["severity"]]):
            lines.append(f"- {icon.get(a['severity'], '⚪')} **{a['severity'].upper()}** — {a['message']}")
        lines.append("")
    else:
        lines += ["## Alerts", "", "🟢 No anomalies detected in this snapshot.", ""]

    lines += ["## Network Performance", "", "| Metric | Value |", "|---|---|"]
    lines += [
        f"| RPC health | {net.get('health', 'N/A')} |",
        f"| Current slot | {_fmt_num(net.get('current_slot'), 0)} |",
        f"| Block height | {_fmt_num(net.get('block_height'), 0)} |",
        f"| Epoch | {net.get('epoch', 'N/A')} |",
        f"| Epoch progress | {_fmt_pct(net.get('epoch_progress_pct')).replace('+','')} |",
        f"| Current TPS | {_fmt_num(net.get('current_tps'))} |",
        f"| Avg TPS | {_fmt_num(net.get('avg_tps'))} |",
        f"| Max / Min TPS | {_fmt_num(net.get('max_tps'))} / {_fmt_num(net.get('min_tps'))} |",
        f"| Avg slot time | {_fmt_num(net.get('avg_slot_time_ms'), 1)} ms |",
        "",
        "## Validator Status", "", "| Metric | Value |", "|---|---|",
        f"| Active validators | {_fmt_num(val.get('active_count'), 0)} |",
        f"| Delinquent validators | {_fmt_num(val.get('delinquent_count'), 0)} |",
        f"| Delinquent (% of active stake) | {_fmt_pct(val.get('delinquent_stake_pct')).replace('+','')} |",
        f"| Total active stake | {_fmt_num(val.get('total_active_stake_sol'), 0)} SOL |",
    ]
    conc = val.get("stake_concentration") or {}
    lines += [f"| Validators controlling 33% of stake | {conc.get('validators_to_control_33pct', 'N/A')} |", ""]

    lines += ["## Network Activity", "", "| Metric | Value |", "|---|---|"]
    lines += [f"| Daily active addresses | {_fmt_num(activity.get('value'), 0)} |", f"| Activity source | {activity.get('source', 'N/A')} |", f"| Activity date | {activity.get('date', 'N/A')} |"]
    if activity.get("_note"):
        lines.append(f"| Dune status | {activity['_note']} |")
    lines.append("")

    lines += ["## SOL Supply", "", f"- Total: {_fmt_num(supply.get('total_sol'), 0)} SOL", f"- Circulating: {_fmt_num(supply.get('circulating_sol'), 0)} SOL", f"- Non-circulating: {_fmt_num(supply.get('non_circulating_sol'), 0)} SOL", ""]

    lines += ["## Economic Indicators", "", "| Metric | Value |", "|---|---|"]
    lines += [
        f"| SOL price | {_fmt_usd(market.get('price_usd'))} |",
        f"| SOL 24h change | {_fmt_pct(market.get('price_change_pct_24h'))} |",
        f"| SOL 24h volume | {_fmt_usd(market.get('volume_24h_usd'))} |",
        f"| SOL market cap | {_fmt_usd(market.get('market_cap_usd'))} |",
        f"| Solana chain TVL | {_fmt_usd(tvl.get('tvl_usd'))} |",
        f"| TVL change (24h) | {_fmt_pct(tvl.get('tvl_change_pct_24h'))} |",
        f"| TVL change (7d) | {_fmt_pct(tvl.get('tvl_change_pct_7d'))} |",
        f"| Stablecoin supply on Solana | {_fmt_usd(stable.get('total_stablecoin_supply_usd'))} |",
        f"| DEX volume (24h) | {_fmt_usd(dex.get('dex_volume_24h_usd'))} |",
        f"| Chain revenue / REV proxy (24h) | {_fmt_usd(fees.get('chain_revenue_24h_usd'))} |", "",
    ]

    lines += ["## Ecosystem & Community Watchlist", ""]
    if social.get("_note"):
        lines += [f"_{social['_note']}_", ""]
    for acc in social.get("accounts", []):
        lines.append(f"- **{acc['handle']}** — {acc['reason']}")
        for t in acc.get("recent_tweets", [])[:3]:
            lines.append(f"  - {t.get('date', '')}: {t.get('content', '')[:200]} ({t.get('url', '')})")
    lines.append("")

    lines += ["## Upcoming Upgrades & Developments", ""]
    for u in upcoming:
        lines.append(f"- **{u['name']}** — {u['description']} ([track]({u['track']}))")
    lines += ["", "---", "", "_Generated automatically by SolBeat. The outlook is a data-driven summary, not investment advice._", ""]
    return "\n".join(lines)
