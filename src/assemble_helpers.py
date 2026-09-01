"""Small, deterministic narrative helpers for the landing-page outlook."""


def _pct_change(new_value, old_value):
    if new_value is None or old_value in (None, 0):
        return None
    return 100 * (new_value - old_value) / old_value


def _direction(value):
    if value is None or value == 0:
        return "flat"
    return "up" if value > 0 else "down"


def _latest_7d_price_change(report):
    series = (((report.get("market") or {}).get("trend_7d") or {}).get("seven_day_series") or [])
    points = [p for p in series if p.get("price_usd") is not None]
    if len(points) < 2:
        return None
    return _pct_change(points[-1]["price_usd"], points[0]["price_usd"])


def build_outlook(report):
    market = (report.get("market") or {}).get("price") or {}
    tvl = ((report.get("defi") or {}).get("tvl") or {})
    validators = report.get("validators") or {}
    network = report.get("network_performance") or {}
    activity = report.get("daily_active_addresses") or {}
    status = ((report.get("solana_network_status") or {}).get("current") or {})

    # The outlook intentionally uses 7-day trend measurements for economic
    # activity rather than noisy 24-hour moves. Live operational/validator
    # health remains a current-state signal because those are safety/status
    # conditions, not short-term market trends.
    price_change_7d = _latest_7d_price_change(report)
    tvl_change_7d = tvl.get("tvl_change_pct_7d")
    active_change_7d = activity.get("change_pct_7d")
    active_avg_7d = activity.get("average_7d")
    delinquent = validators.get("delinquent_stake_pct")
    slot_time = network.get("avg_slot_time_ms")
    operational = status.get("indicator") in (None, "none")

    positives, risks = [], []
    if operational:
        positives.append("the network is operational")
    if slot_time is not None and slot_time <= 500:
        positives.append("recent slot times remain healthy")
    if tvl_change_7d is not None and tvl_change_7d > 0:
        positives.append(f"DeFi TVL is up {tvl_change_7d:.1f}% over 7d")
    if active_avg_7d is not None:
        if active_change_7d is not None:
            positives.append(f"Dune averages about {active_avg_7d:,.0f} daily active addresses over 7d ({active_change_7d:+.1f}% vs the prior 7d point)")
        else:
            positives.append(f"Dune averages about {active_avg_7d:,.0f} daily active addresses over 7d")
    if price_change_7d is not None and price_change_7d > 0:
        positives.append(f"SOL is up {price_change_7d:.1f}% over 7d")

    if delinquent is not None and delinquent >= 5:
        risks.append(f"{delinquent:.2f}% of stake is delinquent")
    if slot_time is not None and slot_time > 500:
        risks.append("slot times are elevated")
    if tvl_change_7d is not None and tvl_change_7d < -5:
        risks.append(f"DeFi TVL is down {abs(tvl_change_7d):.1f}% over 7d")
    if price_change_7d is not None and price_change_7d < -8:
        risks.append(f"SOL is down {abs(price_change_7d):.1f}% over 7d")
    if active_change_7d is not None and active_change_7d < -15:
        risks.append(f"7d activity trend is weakening ({active_change_7d:.1f}%)")
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
        "window": "7d",
        "method": "Deterministic synthesis using 7-day SOL price, DeFi TVL, and activity trends plus current network, validator, and Solana Status health signals; it is not investment advice.",
    }
