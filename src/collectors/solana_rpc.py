"""
Direct Solana JSON-RPC collector.

Uses only the public JSON-RPC methods listed in the bounty spec:
getSlot, getBlockTime, getEpochInfo, getRecentPerformanceSamples,
getVoteAccounts, getBalance, getSignaturesForAddress, getHealth, getSupply.

No SDK required — plain JSON-RPC over HTTP via urllib (see http_client.py).
"""

import time

from .. import config
from ..http_client import post_json, SourceUnavailable
from . import stakewiz

_RPC_ID = 0


def _rpc(method, params=None):
    global _RPC_ID
    _RPC_ID += 1
    payload = {
        "jsonrpc": "2.0",
        "id": _RPC_ID,
        "method": method,
        "params": params or [],
    }
    resp = post_json(config.SOLANA_RPC_URL, payload)
    if "error" in resp:
        raise SourceUnavailable(f"RPC {method} returned error: {resp['error']}")
    return resp.get("result")


def get_health():
    try:
        return _rpc("getHealth")
    except SourceUnavailable:
        return None


def get_slot():
    return _rpc("getSlot")


def get_block_time(slot):
    try:
        return _rpc("getBlockTime", [slot])
    except SourceUnavailable:
        return None


def get_epoch_info():
    return _rpc("getEpochInfo")


def get_recent_performance_samples(limit=None):
    limit = limit or config.PERFORMANCE_SAMPLE_LIMIT
    return _rpc("getRecentPerformanceSamples", [limit])


def get_vote_accounts():
    return _rpc("getVoteAccounts")


def get_supply():
    return _rpc("getSupply")


def get_balance(pubkey):
    result = _rpc("getBalance", [pubkey])
    if result is None:
        return None
    return result.get("value")


def get_signatures_for_address(pubkey, limit=10):
    return _rpc("getSignaturesForAddress", [pubkey, {"limit": limit}])


def _compute_tps_stats(samples):
    """Turn getRecentPerformanceSamples output into a TPS summary."""
    if not samples:
        return {"current_tps": None, "avg_tps": None, "max_tps": None, "min_tps": None, "samples_used": 0}

    tps_values = []
    for s in samples:
        secs = s.get("samplePeriodSecs") or 60
        txs = s.get("numTransactions") or 0
        if secs > 0:
            tps_values.append(txs / secs)

    if not tps_values:
        return {"current_tps": None, "avg_tps": None, "max_tps": None, "min_tps": None, "samples_used": 0}

    return {
        "current_tps": round(tps_values[0], 2),
        "avg_tps": round(sum(tps_values) / len(tps_values), 2),
        "max_tps": round(max(tps_values), 2),
        "min_tps": round(min(tps_values), 2),
        "samples_used": len(tps_values),
    }


def _compute_slot_time_stats(samples):
    """Average ms-per-slot across samples (target on Solana is ~400ms/slot)."""
    if not samples:
        return {"avg_slot_time_ms": None}
    ratios = []
    for s in samples:
        secs = s.get("samplePeriodSecs") or 0
        slots = s.get("numSlots") or 0
        if slots > 0:
            ratios.append((secs / slots) * 1000)
    if not ratios:
        return {"avg_slot_time_ms": None}
    return {"avg_slot_time_ms": round(sum(ratios) / len(ratios), 1)}


def _lamports_to_sol(lamports):
    if lamports is None:
        return None
    return lamports / 1_000_000_000


def collect_network_performance():
    """Network performance section: slot, epoch, TPS, slot time, health."""
    errors = []
    out = {}

    try:
        out["health"] = get_health()
    except SourceUnavailable as e:
        errors.append(str(e))
        out["health"] = None

    try:
        slot = get_slot()
        out["current_slot"] = slot
        out["block_time_unix"] = get_block_time(slot) if slot is not None else None
    except SourceUnavailable as e:
        errors.append(str(e))
        out["current_slot"] = None
        out["block_time_unix"] = None

    try:
        epoch_info = get_epoch_info()
        out["epoch"] = epoch_info.get("epoch") if epoch_info else None
        out["slot_index"] = epoch_info.get("slotIndex") if epoch_info else None
        out["slots_in_epoch"] = epoch_info.get("slotsInEpoch") if epoch_info else None
        if epoch_info and epoch_info.get("slotsInEpoch"):
            out["epoch_progress_pct"] = round(
                100 * epoch_info["slotIndex"] / epoch_info["slotsInEpoch"], 2
            )
        else:
            out["epoch_progress_pct"] = None
        out["block_height"] = epoch_info.get("blockHeight") if epoch_info else None
    except SourceUnavailable as e:
        errors.append(str(e))
        out.update({
            "epoch": None, "slot_index": None, "slots_in_epoch": None,
            "epoch_progress_pct": None, "block_height": None,
        })

    try:
        samples = get_recent_performance_samples()
        out.update(_compute_tps_stats(samples))
        out.update(_compute_slot_time_stats(samples))
    except SourceUnavailable as e:
        errors.append(str(e))
        out.update({
            "current_tps": None, "avg_tps": None, "max_tps": None,
            "min_tps": None, "samples_used": 0, "avg_slot_time_ms": None,
        })

    out["collected_at_unix"] = int(time.time())
    if errors:
        out["_errors"] = errors
    return out


def collect_validators():
    """Validator status: active vs delinquent, stake distribution, top validators."""
    errors = []
    out = {}
    try:
        vote_accounts = get_vote_accounts()
    except SourceUnavailable as e:
        return {"_errors": [str(e)], "active_count": None, "delinquent_count": None}

    current = vote_accounts.get("current", [])
    delinquent = vote_accounts.get("delinquent", [])

    total_active_stake = sum(v.get("activatedStake", 0) for v in current)
    total_delinquent_stake = sum(v.get("activatedStake", 0) for v in delinquent)
    total_stake = total_active_stake + total_delinquent_stake

    top_validators = sorted(current, key=lambda v: v.get("activatedStake", 0), reverse=True)
    top_validators = top_validators[: config.TOP_VALIDATOR_COUNT]

    out["active_count"] = len(current)
    out["delinquent_count"] = len(delinquent)
    out["total_validator_count"] = len(current) + len(delinquent)
    out["delinquent_pct_of_validators"] = (
        round(100 * len(delinquent) / (len(current) + len(delinquent)), 2)
        if (current or delinquent) else None
    )
    out["total_active_stake_sol"] = round(_lamports_to_sol(total_active_stake), 2)
    out["total_delinquent_stake_sol"] = round(_lamports_to_sol(total_delinquent_stake), 2)
    out["delinquent_stake_pct"] = (
        round(100 * total_delinquent_stake / total_stake, 3) if total_stake else None
    )
    out["top_validators"] = [
        {
            "vote_pubkey": v.get("votePubkey"),
            "node_pubkey": v.get("nodePubkey"),
            "activated_stake_sol": round(_lamports_to_sol(v.get("activatedStake", 0)), 2),
            "commission_pct": v.get("commission"),
            "last_vote": v.get("lastVote"),
            "root_slot": v.get("rootSlot"),
        }
        for v in top_validators
    ]
    # Best-effort identity enrichment (operator name / Twitter) via Stakewiz.
    # Degrades to None/None per validator if the identity map is empty or a
    # given vote account isn't in it — the dashboard falls back to a
    # shortened address in that case.
    identity_map = stakewiz.collect_identity_map()
    for entry in out["top_validators"]:
        identity = identity_map.get(entry["vote_pubkey"], {})
        entry["name"] = identity.get("name")
        entry["website"] = identity.get("website")

    # Nakamoto-coefficient-style stat: how many validators to reach 33% of stake
    out["stake_concentration"] = _stake_concentration(current, total_active_stake)

    if errors:
        out["_errors"] = errors
    return out


def _stake_concentration(current_validators, total_active_stake):
    if not current_validators or not total_active_stake:
        return None
    sorted_stakes = sorted(
        (v.get("activatedStake", 0) for v in current_validators), reverse=True
    )
    running = 0
    for i, stake in enumerate(sorted_stakes, start=1):
        running += stake
        if running >= 0.33 * total_active_stake:
            return {"validators_to_control_33pct": i}
    return {"validators_to_control_33pct": len(sorted_stakes)}


def collect_supply():
    try:
        supply = get_supply()
    except SourceUnavailable as e:
        return {"_errors": [str(e)]}
    value = (supply or {}).get("value", {})
    return {
        "total_sol": round(_lamports_to_sol(value.get("total")), 2) if value.get("total") is not None else None,
        "circulating_sol": round(_lamports_to_sol(value.get("circulating")), 2) if value.get("circulating") is not None else None,
        "non_circulating_sol": round(_lamports_to_sol(value.get("nonCirculating")), 2) if value.get("nonCirculating") is not None else None,
    }
