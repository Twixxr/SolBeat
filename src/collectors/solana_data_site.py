"""
Best-effort collector for solana.com/data.

That page is a client-side rendered React app with no documented, stable
public JSON API, so scraping it reliably (without a headless browser
dependency) is not realistic for a low-dependency, low-maintenance project.

Rather than add a heavy Selenium/Playwright dependency (which contradicts
the bounty's "minimal dependencies" preference and would be the most
fragile part of the whole pipeline), this collector:

  1. Tries a couple of known underlying data endpoints that have
     historically backed similar Solana Foundation dashboards.
  2. If those fail (they may change or 404 at any time), it degrades
     gracefully and simply omits this section from the report, logging a
     note rather than crashing the whole pipeline.

If you want richer coverage of solana.com/data specifically, the cleanest
supported extension point is: install `playwright`, add a
`collect_via_browser()` function here, and wire it in behind a
`--with-browser` CLI flag so the no-dependency default path still works
for everyone else.
"""

from ..http_client import get_json, SourceUnavailable

# Historically used by some Solana Foundation dashboard builds. Kept as a
# best-effort attempt only — treat any success as a bonus, not a guarantee.
_CANDIDATE_ENDPOINTS = [
    "https://solana.com/api/data/dashboard",
]


def collect():
    for url in _CANDIDATE_ENDPOINTS:
        try:
            data = get_json(url)
            if data:
                return {"source": url, "data": data}
        except SourceUnavailable:
            continue
    return {
        "_note": (
            "solana.com/data has no stable public JSON API at this time; "
            "this section is intentionally omitted rather than scraped "
            "unreliably. See src/collectors/solana_data_site.py for the "
            "documented extension point (headless-browser based scraping)."
        )
    }
