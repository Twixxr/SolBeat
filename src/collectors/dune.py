"""Optional Dune collector for Solana daily active addresses."""

import datetime
import json
import urllib.error
import urllib.request

from .. import config


def _get_json(url, api_key):
    req = urllib.request.Request(url, headers={
        "X-Dune-API-Key": api_key,
        "Accept": "application/json",
        "User-Agent": config.USER_AGENT,
    }, method="GET")
    with urllib.request.urlopen(req, timeout=config.HTTP_TIMEOUT_SECONDS) as response:
        return json.loads(response.read().decode("utf-8"))


def _date_key(row):
    for key, value in row.items():
        name = str(key).lower()
        if any(token in name for token in ("date", "day", "time")):
            text = str(value)
            try:
                return datetime.datetime.fromisoformat(text.replace("Z", "+00:00")).timestamp()
            except ValueError:
                return 0
    return 0


def _active_value(row):
    candidates = []
    for key, value in row.items():
        name = str(key).lower()
        if any(token in name for token in ("date", "day", "time")):
            continue
        try:
            numeric = float(value)
        except (TypeError, ValueError):
            continue
        candidates.append((name, numeric))
    preferred = [x for x in candidates if any(t in x[0] for t in ("active", "address", "wallet", "dau"))]
    chosen = preferred[0] if preferred else (candidates[0] if candidates else None)
    return chosen[1] if chosen else None


def _pct_change(new_value, old_value):
    if new_value is None or old_value in (None, 0):
        return None
    return round(100 * (new_value - old_value) / old_value, 2)


def collect_daily_active_addresses():
    api_key = config.DUNE_API_KEY
    query_id = config.DUNE_ACTIVE_ADDRESSES_QUERY_ID
    base = {"source": "Dune", "query_id": query_id, "configured": bool(api_key)}

    if not api_key:
        return {**base, "value": None, "date": None,
                "average_7d": None, "change_pct_7d": None,
                "_note": "Dune is not configured. Add the DUNE_API_KEY GitHub Actions secret to enable daily active addresses."}

    try:
        payload = _get_json(
            f"{config.DUNE_API_URL}/api/v1/query/{query_id}/results?limit=100",
            api_key,
        )
        rows = ((payload.get("result") or {}).get("rows") or [])
        dated = sorted(
            ((row, _date_key(row), _active_value(row)) for row in rows),
            key=lambda item: item[1],
        )
        dated = [item for item in dated if item[1] > 0 and item[2] is not None]
        if not dated:
            return {**base, "value": None, "date": None,
                    "average_7d": None, "change_pct_7d": None,
                    "_note": "Dune returned no recognizable dated active-address rows."}

        latest_row, _, latest_value = dated[-1]
        recent = [item[2] for item in dated[-7:]]
        prior = [item[2] for item in dated[-14:-7]]
        average_7d = sum(recent) / len(recent)
        prior_average_7d = sum(prior) / len(prior) if prior else None

        date_value = None
        for key, value in latest_row.items():
            if any(token in str(key).lower() for token in ("date", "day", "time")):
                date_value = value
                break

        return {
            **base,
            "value": int(round(latest_value)),
            "date": date_value,
            "average_7d": int(round(average_7d)),
            "change_pct_7d": _pct_change(average_7d, prior_average_7d),
            "_note": None,
        }
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, json.JSONDecodeError, ValueError) as exc:
        return {**base, "value": None, "date": None,
                "average_7d": None, "change_pct_7d": None,
                "_note": f"Dune active-address collection failed: {exc}"}
