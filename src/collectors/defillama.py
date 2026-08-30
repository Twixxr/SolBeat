"""
DeFiLlama collector — no API key required for any of these public endpoints.

Covers:
- Solana chain TVL (current + 24h change, derived from historical series)
- Stablecoin supply on Solana
- DEX volume on Solana (24h)
- Fees / Real Economic Value (REV) on Solana (24h)
"""

from .. import config
from ..http_client import get_json, SourceUnavailable


def _safe_get(url):
    try:
        return get_json(url), None
    except SourceUnavailable as e:
        return None, str(e)


def collect_chain_tvl():
    data, err = _safe_get(config.DEFILLAMA_CHAIN_TVL_URL)
    if err or not data:
        return {"_errors": [err] if err else ["empty response"]}

    # data is a list of {"date": unix_seconds, "tvl": float}, sorted ascending
    data_sorted = sorted(data, key=lambda d: d["date"])
    latest = data_sorted[-1]
    out = {"tvl_usd": round(latest["tvl"], 2), "as_of_unix": latest["date"]}

    # 24h change: find the point closest to 24h before latest
    target = latest["date"] - 86400
    prior = min(data_sorted, key=lambda d: abs(d["date"] - target))
    if prior["tvl"]:
        out["tvl_change_pct_24h"] = round(100 * (latest["tvl"] - prior["tvl"]) / prior["tvl"], 2)
    else:
        out["tvl_change_pct_24h"] = None

    # 7d change
    target7 = latest["date"] - 7 * 86400
    prior7 = min(data_sorted, key=lambda d: abs(d["date"] - target7))
    if prior7["tvl"]:
        out["tvl_change_pct_7d"] = round(100 * (latest["tvl"] - prior7["tvl"]) / prior7["tvl"], 2)
    else:
        out["tvl_change_pct_7d"] = None

    return out


def collect_stablecoin_supply():
    data, err = _safe_get(config.DEFILLAMA_STABLECOINS_URL)
    if err or not data:
        return {"_errors": [err] if err else ["empty response"]}

    solana_entry = next((d for d in data if d.get("name") == "Solana"), None)
    if not solana_entry:
        return {"_errors": ["Solana not found in stablecoinchains response"]}

    total_circulating = solana_entry.get("totalCirculatingUSD", {})
    # totalCirculatingUSD is typically {"peggedUSD": <amount>, ...}
    total_usd = sum(v for v in total_circulating.values() if isinstance(v, (int, float)))
    return {
        "total_stablecoin_supply_usd": round(total_usd, 2),
        "breakdown": total_circulating,
    }


def collect_dex_volume():
    data, err = _safe_get(config.DEFILLAMA_DEX_VOLUME_URL)
    if err or not data:
        return {"_errors": [err] if err else ["empty response"]}
    return {
        "dex_volume_24h_usd": data.get("total24h"),
        "dex_volume_change_pct_24h": data.get("change_1d"),
        "top_dexs_by_volume": [
            {"name": p.get("name"), "volume_24h_usd": p.get("total24h")}
            for p in sorted(
                data.get("protocols", []),
                key=lambda p: p.get("total24h") or 0,
                reverse=True,
            )[:10]
        ] if data.get("protocols") else [],
    }


def collect_fees_and_rev():
    data, err = _safe_get(config.DEFILLAMA_FEES_REV_URL)
    if err or not data:
        return {"_errors": [err] if err else ["empty response"]}
    return {
        "chain_revenue_24h_usd": data.get("total24h"),
        "chain_revenue_change_pct_24h": data.get("change_1d"),
    }


def collect_top_protocols(limit=15):
    """
    Break Solana chain TVL down by individual **onchain** DeFi protocol
    (e.g. Jupiter, Kamino, ONRE, Solstice...) rather than the aggregate
    chain total. Centralized exchanges (DeFiLlama category "CEX") are
    excluded — those aren't onchain DeFi and would misrepresent this as
    a protocol breakdown when it's really a mix of onchain contracts and
    off-chain custodial balances.
    """
    data, err = _safe_get(config.DEFILLAMA_PROTOCOLS_URL)
    if err or not data:
        return {"_errors": [err] if err else ["empty response"]}

    EXCLUDED_CATEGORIES = {"CEX"}

    solana_protocols = []
    for p in data:
        if p.get("category") in EXCLUDED_CATEGORIES:
            continue
        chain_tvls = p.get("chainTvls", {})
        solana_tvl = chain_tvls.get("Solana")
        if solana_tvl is None:
            continue
        solana_protocols.append({
            "name": p.get("name"),
            "category": p.get("category"),
            "tvl_usd": round(solana_tvl, 2),
            "change_1d_pct": p.get("change_1d"),
            "url": p.get("url"),
        })

    solana_protocols.sort(key=lambda p: p["tvl_usd"], reverse=True)
    top = solana_protocols[:limit]

    total_tvl = sum(p["tvl_usd"] for p in solana_protocols)
    for p in top:
        p["pct_of_solana_tvl"] = round(100 * p["tvl_usd"] / total_tvl, 2) if total_tvl else None

    return {
        "protocols": top,
        "protocol_count": len(solana_protocols),
        "categories": _aggregate_by_category(solana_protocols, total_tvl),
    }


def _aggregate_by_category(solana_protocols, total_tvl):
    """
    TVL grouped by protocol category (Lending, DEX, Liquid Staking, CDP,
    Yield, Bridge, etc.) across ALL onchain Solana protocols DeFiLlama
    tracks — not just the top N. This mirrors the category breakdown
    DeFiLlama's own chain page (defillama.com/chain/solana) leads with,
    computed from data already being fetched for the protocol list above
    (no extra API calls needed).
    """
    buckets = {}
    for p in solana_protocols:
        category = p.get("category") or "Other"
        buckets[category] = buckets.get(category, 0) + p["tvl_usd"]

    categories = [
        {
            "category": name,
            "tvl_usd": round(tvl, 2),
            "pct_of_solana_tvl": round(100 * tvl / total_tvl, 2) if total_tvl else None,
        }
        for name, tvl in buckets.items()
    ]
    categories.sort(key=lambda c: c["tvl_usd"], reverse=True)
    return categories


def collect_all():
    return {
        "tvl": collect_chain_tvl(),
        "stablecoins": collect_stablecoin_supply(),
        "dex_volume": collect_dex_volume(),
        "fees_and_rev": collect_fees_and_rev(),
        "top_protocols": collect_top_protocols(),
    }


# ---------------------------------------------------------------------------
# Long-run (multi-year) daily history, for the dashboard's expanded charts.
# DeFiLlama keeps full daily history for these metrics going back to when
# each first appeared on their platform — no key required.
# ---------------------------------------------------------------------------

def collect_tvl_history():
    data, err = _safe_get(config.DEFILLAMA_CHAIN_TVL_URL)
    if err or not data:
        return {"_errors": [err] if err else ["empty response"]}
    data_sorted = sorted(data, key=lambda d: d["date"])
    trimmed = data_sorted[-config.LONG_HISTORY_MAX_POINTS:]
    return {"series": [{"date_unix": d["date"], "value": round(d["tvl"], 2)} for d in trimmed]}


def collect_stablecoin_history():
    data, err = _safe_get(config.DEFILLAMA_STABLECOIN_CHART_URL)
    if err or not data:
        return {"_errors": [err] if err else ["empty response"]}
    series = []
    for d in data:
        try:
            date_unix = int(d.get("date"))
        except (TypeError, ValueError):
            continue
        total = d.get("totalCirculating", {}) or {}
        usd = sum(v for v in total.values() if isinstance(v, (int, float)))
        series.append({"date_unix": date_unix, "value": round(usd, 2)})
    series = series[-config.LONG_HISTORY_MAX_POINTS:]
    return {"series": series}


def collect_dex_volume_history():
    data, err = _safe_get(config.DEFILLAMA_DEX_VOLUME_CHART_URL)
    if err or not data:
        return {"_errors": [err] if err else ["empty response"]}
    chart = data.get("totalDataChart", [])
    series = [{"date_unix": int(p[0]), "value": p[1]} for p in chart]
    series = series[-config.LONG_HISTORY_MAX_POINTS:]
    return {"series": series}


def collect_fees_history():
    data, err = _safe_get(config.DEFILLAMA_FEES_CHART_URL)
    if err or not data:
        return {"_errors": [err] if err else ["empty response"]}
    chart = data.get("totalDataChart", [])
    series = [{"date_unix": int(p[0]), "value": p[1]} for p in chart]
    series = series[-config.LONG_HISTORY_MAX_POINTS:]
    return {"series": series}
