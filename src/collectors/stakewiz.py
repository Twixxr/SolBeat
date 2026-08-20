"""
Best-effort validator identity enrichment via the free, keyless Stakewiz API
(https://api.stakewiz.com), which aggregates Solana validator on-chain vote
accounts with self-reported off-chain identity info that validator
operators optionally publish.

Confirmed live response fields (as of this writing) include "name" and
"website" — there is NO dedicated Twitter/X field in this API. When an
operator's published website happens to be a twitter.com/x.com URL, the
dashboard treats it as their social link; otherwise it's shown as a
regular website link. Not every operator publishes either field.

This module never raises; it returns an empty map on any failure.
"""

from .. import http_client
from ..http_client import SourceUnavailable

STAKEWIZ_VALIDATORS_URL = "https://api.stakewiz.com/validators"


def collect_identity_map():
    """
    Returns { vote_pubkey: {"name": str|None, "website": str|None} }.
    Empty dict on any failure or unexpected response shape.
    """
    try:
        data = http_client.get_json(STAKEWIZ_VALIDATORS_URL)
    except SourceUnavailable:
        return {}
    if not isinstance(data, list):
        return {}

    identity_map = {}
    for entry in data:
        if not isinstance(entry, dict):
            continue
        vote_key = entry.get("vote_identity") or entry.get("vote_pubkey") or entry.get("voteAccount")
        if not vote_key:
            continue

        name = entry.get("name") or entry.get("moniker")
        website = entry.get("website")

        if name or website:
            identity_map[vote_key] = {"name": name, "website": website}

    return identity_map
