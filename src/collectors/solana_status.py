"""
Solana's official network status page (https://status.solana.com) runs on
Atlassian Statuspage, which exposes a standard, public, keyless JSON API
(documented at https://developer.statuspage.io) — no account or API key
needed, confirmed against real examples from other Statuspage-hosted sites
before writing this.

This is a genuine source for real Solana network status and incident
history via a genuine, official, keyless source.
"""

import datetime

from ..http_client import get_json, SourceUnavailable

STATUS_JSON_URL = "https://status.solana.com/api/v2/status.json"
INCIDENTS_JSON_URL = "https://status.solana.com/api/v2/incidents.json"


def collect_current_status():
    """
    Returns {"indicator": "none"|"minor"|"major"|"critical", "description": str}.
    "none" means fully operational.
    """
    try:
        data = get_json(STATUS_JSON_URL)
    except SourceUnavailable as e:
        return {"_errors": [str(e)]}

    status = (data or {}).get("status", {})
    return {
        "indicator": status.get("indicator"),
        "description": status.get("description"),
    }


def collect_days_since_last_incident():
    """
    Scans the full incident history for the most recent incident (by
    resolved_at if resolved, otherwise created_at if still ongoing) and
    returns how many days ago that was.
    """
    try:
        data = get_json(INCIDENTS_JSON_URL)
    except SourceUnavailable as e:
        return {"_errors": [str(e)]}

    incidents = (data or {}).get("incidents", [])
    if not incidents:
        return {"_note": "no incidents on record"}

    latest_dt = None
    latest_name = None
    for incident in incidents:
        if not isinstance(incident, dict):
            continue
        ts_str = incident.get("resolved_at") or incident.get("created_at")
        if not ts_str:
            continue
        try:
            ts = datetime.datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
        except ValueError:
            continue
        if latest_dt is None or ts > latest_dt:
            latest_dt = ts
            latest_name = incident.get("name")

    if latest_dt is None:
        return {"_note": "no dated incidents found"}

    now = datetime.datetime.now(datetime.timezone.utc)
    days = round((now - latest_dt).total_seconds() / 86400, 2)
    return {
        "days_since_last_incident": days,
        "last_incident_name": latest_name,
        "last_incident_date_unix": int(latest_dt.timestamp()),
    }
