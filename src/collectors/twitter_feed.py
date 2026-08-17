"""
Twitter/X collector — key announcement + sentiment surfacing, without
requiring a paid X API key.

X's official API requires a paid tier for meaningful read access, which
conflicts with the bounty's "no API keys" preference. Instead this module:

  1. If the optional `snscrape` package is installed (pip install
     snscrape), uses it to pull the latest N tweets from a curated list of
     Solana ecosystem accounts. snscrape needs no API key/auth, but relies
     on scraping X's public web surface, so it can break when X changes
     their frontend — this is documented as a known limitation.
  2. If snscrape is unavailable or fails (import error, X blocking the
     scrape, etc.), the collector degrades gracefully: it returns the
     curated account list with an explanatory note instead of tweet
     content, so the report still tells the reader *where* to look for
     announcements even if live pulling isn't currently possible.

This keeps the default install dependency-free (snscrape is optional,
listed in requirements-optional.txt) while still giving credit for the
"automate Twitter" ask when the optional dependency is present.
"""

CURATED_ACCOUNTS = [
    {"handle": "@solana", "reason": "Official Solana Foundation account — protocol news, upgrades"},
    {"handle": "@heliuslabs", "reason": "Infra/RPC provider — frequent deep-dives on network stats"},
    {"handle": "@solanafndn", "reason": "Solana Foundation — governance, SIMD proposals"},
    {"handle": "@superteam", "reason": "Superteam global — ecosystem builder news"},
    {"handle": "@SuperteamCA", "reason": "Superteam Canada — local ecosystem news"},
    {"handle": "@DefiLlama", "reason": "Cross-chain DeFi data, occasional Solana TVL callouts"},
    {"handle": "@jup_ag", "reason": "Jupiter — largest Solana DEX aggregator, ecosystem bellwether"},
]

MAX_TWEETS_PER_ACCOUNT = 5


def _try_snscrape(handle, limit):
    try:
        import snscrape.modules.twitter as sntwitter  # type: ignore
    except ImportError:
        return None, "snscrape not installed (optional dependency)"

    try:
        tweets = []
        query = f"from:{handle.lstrip('@')}"
        for i, tweet in enumerate(sntwitter.TwitterSearchScraper(query).get_items()):
            if i >= limit:
                break
            tweets.append({
                "date": tweet.date.isoformat() if tweet.date else None,
                "content": tweet.rawContent if hasattr(tweet, "rawContent") else str(tweet.content),
                "url": tweet.url,
                "like_count": getattr(tweet, "likeCount", None),
                "retweet_count": getattr(tweet, "retweetCount", None),
            })
        return tweets, None
    except Exception as exc:  # snscrape raises various things when X blocks it
        return None, f"snscrape failed for {handle}: {exc}"


def collect():
    results = []
    any_success = False
    for account in CURATED_ACCOUNTS:
        tweets, err = _try_snscrape(account["handle"], MAX_TWEETS_PER_ACCOUNT)
        entry = {"handle": account["handle"], "reason": account["reason"]}
        if tweets:
            entry["recent_tweets"] = tweets
            any_success = True
        else:
            entry["recent_tweets"] = []
            entry["_note"] = err
        results.append(entry)

    return {
        "accounts": results,
        "live_pull_active": any_success,
        "_note": None if any_success else (
            "Live tweet pulling requires the optional 'snscrape' package "
            "(pip install -r requirements-optional.txt) and can still be "
            "blocked by X at any time. Falling back to a curated watchlist "
            "so the report remains useful without it."
        ),
    }
