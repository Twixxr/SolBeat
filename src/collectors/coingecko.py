"""
CoinGecko collector — uses the free, keyless public API endpoints.

Note: the free tier is rate-limited (roughly 10-30 calls/min shared across
all anonymous users). If you hit 429s frequently, either lower your refresh
frequency, or set COINGECKO_API_KEY in the environment and adapt
config.COINGECKO_PRICE_URL to use the pro/demo host — left as a documented
extension point since the bounty prioritizes no-key solutions.
"""

from .. import config
from ..http_client import get_json, SourceUnavailable


def collect_price():
    try:
        data = get_json(config.COINGECKO_PRICE_URL)
    except SourceUnavailable as e:
        return {"_errors": [str(e)]}

    sol = data.get("solana", {})
    return {
        "price_usd": sol.get("usd"),
        "price_change_pct_24h": round(sol.get("usd_24h_change"), 2) if sol.get("usd_24h_change") is not None else None,
        "volume_24h_usd": sol.get("usd_24h_vol"),
        "market_cap_usd": sol.get("usd_market_cap"),
    }


def collect_7d_trend():
    try:
        data = get_json(config.COINGECKO_MARKET_CHART_URL)
    except SourceUnavailable as e:
        return {"_errors": [str(e)]}

    prices = data.get("prices", [])  # list of [unix_ms, price]
    if not prices:
        return {"_errors": ["empty price series"]}

    return {
        "seven_day_series": [
            {"date_unix": int(p[0] / 1000), "price_usd": round(p[1], 4)} for p in prices
        ]
    }


def collect_all():
    return {
        "price": collect_price(),
        "trend_7d": collect_7d_trend(),
    }


def collect_long_history():
    """
    ~2 years of daily price, market cap, and volume for the dashboard's
    expanded charts. Best-effort: CoinGecko's public tier has, at times,
    restricted how far back anonymous requests can go — if this call fails
    or returns nothing, each series comes back empty and the dashboard
    shows "not enough history" for that card rather than breaking.
    """
    try:
        data = get_json(config.COINGECKO_MARKET_CHART_LONG_URL)
    except SourceUnavailable as e:
        err = [str(e)]
        return {"price": {"_errors": err}, "market_cap": {"_errors": err}, "volume": {"_errors": err}}

    prices = data.get("prices", [])
    caps = data.get("market_caps", [])
    vols = data.get("total_volumes", [])

    def _series(points):
        return [{"date_unix": int(p[0] / 1000), "value": round(p[1], 4)} for p in points][-config.LONG_HISTORY_MAX_POINTS:]

    return {
        "price": {"series": _series(prices)},
        "market_cap": {"series": _series(caps)},
        "volume": {"series": _series(vols)},
    }
