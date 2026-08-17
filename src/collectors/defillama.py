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
    Break Solana chain TVL down by individual protocol (e.g. Jupiter,
    Kamino, Marinade...) rather than just the aggregate chain total.

    Note on "coins": DeFiLlama does not expose a single keyless endpoint
    for "TVL by underlying token across an entire chain" — that requires
    per-protocol token-breakdown calls (one request per protocol, which
    would quickly hit rate limits across hundreds of Solana protocols).
    As a practical proxy, we surface the pegged-asset breakdown from the
    stablecoin collector (collect_stablecoin_supply) as the "by coin"
    view, and protocol-level TVL here as the "by protocol" view — matching
    the two most useful cuts DeFiLlama's own UI leads with.
    """
    data, err = _safe_get(config.DEFILLAMA_PROTOCOLS_URL)
    if err or not data:
        return {"_errors": [err] if err else ["empty response"]}

    solana_protocols = []
    for p in data:
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

    return {"protocols": top, "protocol_count": len(solana_protocols)}


def collect_all():
    return {
        "tvl": collect_chain_tvl(),
        "stablecoins": collect_stablecoin_supply(),
        "dex_volume": collect_dex_volume(),
        "fees_and_rev": collect_fees_and_rev(),
        "top_protocols": collect_top_protocols(),
    }
