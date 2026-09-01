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


def collect_daily_active_addresses():
    api_key = config.DUNE_API_KEY
    query_id = config.DUNE_ACTIVE_ADDRESSES_QUERY_ID
    base = {"source": "Dune", "query_id": query_id, "configured": bool(api_key)}

    if not api_key:
        return {**base, "value": None, "date": None,
                "_note": "Dune is not configured. Add the DUNE_API_KEY GitHub Actions secret to enable daily active addresses."}

    try:
        payload = _get_json(
            f"{config.DUNE_API_URL}/api/v1/query/{query_id}/results?limit=100",
            api_key,
        )
        rows = ((payload.get("result") or {}).get("rows") or [])
        if not rows:
            return {**base, "value": None, "date": None,
                    "_note": "Dune returned no rows from the configured active-address query."}

        row = max(rows, key=_date_key)
        candidates, date_value = [], None
        for key, value in row.items():
            name = str(key).lower()
            if any(token in name for token in ("date", "day", "time")):
                date_value = date_value or value
                continue
            try:
                numeric = float(value)
            except (TypeError, ValueError):
                continue
            candidates.append((name, numeric))
        preferred = [x for x in candidates if any(t in x[0] for t in ("active", "address", "wallet", "dau"))]
        chosen = preferred[0] if preferred else (candidates[0] if candidates else None)
        if not chosen:
            return {**base, "value": None, "date": date_value,
                    "_note": "Dune result did not contain a recognizable numeric active-address column."}
        return {**base, "value": int(round(chosen[1])), "date": date_value, "_note": None}
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, json.JSONDecodeError, ValueError) as exc:
        return {**base, "value": None, "date": None,
                "_note": f"Dune active-address collection failed: {exc}"}
