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
