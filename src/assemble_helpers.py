"""Small, deterministic narrative helpers for the landing-page outlook."""


def _direction(value):
    if value is None or value == 0:
        return "flat"
    return "up" if value > 0 else "down"


def build_outlook(report):
    market = (report.get("market") or {}).get("price") or {}
    tvl = ((report.get("defi") or {}).get("tvl") or {})
    validators = report.get("validators") or {}
    network = report.get("network_performance") or {}
    activity = report.get("daily_active_addresses") or {}
    status = ((report.get("solana_network_status") or {}).get("current") or {})

    price_change = market.get("price_change_pct_24h")
    tvl_change = tvl.get("tvl_change_pct_24h")
    delinquent = validators.get("delinquent_stake_pct")
    slot_time = network.get("avg_slot_time_ms")
    active = activity.get("value")
    operational = status.get("indicator") in (None, "none")

    positives, risks = [], []
    if operational:
        positives.append("the network is operational")
    if slot_time is not None and slot_time <= 500:
        positives.append("recent slot times remain healthy")
    if tvl_change is not None and tvl_change > 0:
        positives.append(f"DeFi TVL is rising {tvl_change:.1f}% over 24h")
    if active is not None:
        positives.append(f"Dune reports about {active:,.0f} daily active addresses")
    if price_change is not None and price_change > 0:
        positives.append(f"SOL is up {price_change:.1f}% over 24h")

    if delinquent is not None and delinquent >= 5:
        risks.append(f"{delinquent:.2f}% of stake is delinquent")
    if slot_time is not None and slot_time > 500:
        risks.append("slot times are elevated")
    if tvl_change is not None and tvl_change < -5:
        risks.append(f"DeFi TVL is down {abs(tvl_change):.1f}% over 24h")
    if price_change is not None and price_change < -8:
        risks.append(f"SOL is down {abs(price_change):.1f}% over 24h")
    if not operational:
        risks.append("Solana Status is reporting a network incident")

    if risks and not positives:
        outlook = "Cautious"
    elif risks and len(risks) >= 2:
        outlook = "Mixed"
    elif positives and not risks:
        outlook = "Constructive"
    else:
        outlook = "Mixed / constructive"

    summary = f"Solana's current outlook is {outlook.lower()}. "
    if positives:
        summary += "Positive signals: " + "; ".join(positives[:3]) + ". "
    if risks:
        summary += "Risks to watch: " + "; ".join(risks[:3]) + "."
    else:
        summary += "No major network-health warning is present in the latest automated snapshot."

    return {
        "rating": outlook,
        "summary": summary.strip(),
        "positive_signals": positives,
        "risks_to_watch": risks,
        "method": "Deterministic synthesis of the latest network, validator, market, DeFi, activity, and Solana Status metrics; it is not investment advice.",
    }
