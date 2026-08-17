"""
Tiny HTTP helper shared by all collectors.

Only dependency is `requests` (listed in requirements.txt). Everything else
in this project is Python stdlib. We deliberately keep this dependency-light
per the bounty's "no API keys / minimal dependencies" preference.
"""

import json
import time
import urllib.request
import urllib.error

from . import config


class SourceUnavailable(Exception):
    """Raised when a data source could not be reached after retries.

    Collectors catch this and degrade gracefully (fill in None / omit the
    section) rather than crashing the whole report.
    """


def _do_request(url, method="GET", data=None, headers=None, timeout=None):
    req_headers = {"User-Agent": config.USER_AGENT, "Accept": "application/json"}
    if headers:
        req_headers.update(headers)

    body = None
    if data is not None:
        body = json.dumps(data).encode("utf-8")
        req_headers["Content-Type"] = "application/json"

    req = urllib.request.Request(url, data=body, headers=req_headers, method=method)
    with urllib.request.urlopen(req, timeout=timeout or config.HTTP_TIMEOUT_SECONDS) as resp:
        raw = resp.read()
        return json.loads(raw.decode("utf-8"))


def get_json(url, timeout=None, retries=None):
    """GET a URL and parse JSON, with retry/backoff. Uses stdlib urllib so
    the project has zero required third-party deps for the RPC/data path
    (requests is only used as a convenience import elsewhere if present)."""
    retries = config.HTTP_MAX_RETRIES if retries is None else retries
    last_err = None
    for attempt in range(1, retries + 1):
        try:
            return _do_request(url, method="GET", timeout=timeout)
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError,
                json.JSONDecodeError, ConnectionError) as exc:
            last_err = exc
            if attempt < retries:
                time.sleep(config.HTTP_RETRY_BACKOFF_SECONDS * attempt)
    raise SourceUnavailable(f"GET {url} failed after {retries} attempts: {last_err}")


def post_json(url, payload, timeout=None, retries=None):
    """POST a JSON payload (used for Solana JSON-RPC calls) with retries."""
    retries = config.HTTP_MAX_RETRIES if retries is None else retries
    last_err = None
    for attempt in range(1, retries + 1):
        try:
            return _do_request(url, method="POST", data=payload, timeout=timeout)
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError,
                json.JSONDecodeError, ConnectionError) as exc:
            last_err = exc
            if attempt < retries:
                time.sleep(config.HTTP_RETRY_BACKOFF_SECONDS * attempt)
    raise SourceUnavailable(f"POST {url} failed after {retries} attempts: {last_err}")
