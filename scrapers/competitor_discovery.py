"""
scrapers/competitor_discovery.py

Auto-discovers top baby sleep accounts on Instagram weekly across:
  - Singapore & Southeast Asia (local market)
  - Global (international benchmarks)

Discovery pipeline:
  1. Serper.dev → finds handles from Google search results (records source URLs)
  2. Playwright → scrapes Instagram hashtags to find active accounts
  3. Benchmarks → known follower counts (manually updated monthly — see KNOWN_BENCHMARKS below)
  4. Ranker     → scores and returns top 10 (5 local + 5 global)

NOTE ON SOCIAL BLADE: Social Blade actively blocks headless Playwright scrapers,
so live follower/growth data is not reliably available for free. Instead this
file uses a small hardcoded benchmark table. Update KNOWN_BENCHMARKS by hand
once a month by checking each account's Instagram profile directly — takes
about 5 minutes. Accounts not in the table still appear (discovered via
search/hashtag) but show "follower count unknown" instead of a number.

Cost: $0 — uses Serper free tier + Playwright, no paid scraping services
"""

import asyncio
import re
import json
import urllib.request
from playwright.async_api import async_playwright
from typing import List, Dict
from datetime import datetime


# ── Search queries ────────────────────────────────────────────────────────────
SERPER_QUERIES = {
    "local": [
        "baby sleep consultant Instagram",
        "sleep training consultant Singapore Instagram account",
        "baby sleep coach Malaysia Indonesia Instagram",
        "newborn sleep consultant Southeast Asia Instagram",
    ],
    "global": [
        "best baby sleep consultant Instagram account 2026",
        "top baby sleep training Instagram",
        "viral baby sleep coach Instagram followers",
        "newborn sleep training expert Instagram",
    ],
}

# Instagram hashtags to scrape for active accounts
HASHTAGS = {
    "local":  ["babysleepsingapore", "sleeptrainingsg", "singaporemom", "sgbaby", "babysleepmy"],
    "global": ["babysleep", "sleeptraining", "sleepcoach", "babysleepcoach", "gentlesleeptraining"],
}

# Known global seed handles always included as baseline
GLOBAL_SEEDS = ["takingcarababies", "littlezssleep", "preciouslittlesleep",
                "sleeplady", "babysleepscience"]

# ── Manual follower benchmarks ─────────────────────────────────────────────
# UPDATE THIS MONTHLY: visit each handle's Instagram profile, check the
# follower count shown under their name, and update the number here.
# This is approximate — last verified by you, not live data.
#
# IMPORTANT: every time you update the numbers below, also update
# BENCHMARKS_LAST_UPDATED to today's date (format: "YYYY-MM-DD"). The
# dashboard reads this date to show you when the data was last refreshed
# and to warn you when it's overdue (30+ days old).
BENCHMARKS_LAST_UPDATED = "2026-06-29"

KNOWN_BENCHMARKS = {
    "takingcarababies":     {"followers": 1_900_000, "grade": "A"},
    "littlezssleep":        {"followers": 19_200,    "grade": "B+"},
    "preciouslittlesleep":  {"followers": 20_100,    "grade": "B+"},
    "sleeplady":            {"followers": 12_500,    "grade": "B"},
    "babysleepscience":     {"followers": 8_900,     "grade": "B-"},
}


# ── Main discovery function ───────────────────────────────────────────────────
async def discover_competitors(serper_api_key: str) -> Dict:
    print("  [Discovery] Starting auto-discovery — SG/SEA + Global...")

    # Step 1 — Find handles via Serper (records the source search result URL)
    local_handles  = await _find_handles_serper(SERPER_QUERIES["local"],  serper_api_key, "local")
    global_handles = await _find_handles_serper(SERPER_QUERIES["global"], serper_api_key, "global")

    # Step 2 — Find handles via Instagram hashtags
    ig_local  = await _find_handles_instagram(HASHTAGS["local"][:3])
    ig_global = await _find_handles_instagram(HASHTAGS["global"][:3])

    # Merge: each handle carries its discovery sources
    all_local  = _merge_handles(local_handles,  ig_local,  GLOBAL_SEEDS[:0])
    all_global = _merge_handles(global_handles, ig_global, GLOBAL_SEEDS)

    print(f"  [Discovery] {len(all_local)} local candidates, {len(all_global)} global candidates")

    # Step 3 — Attach known benchmark data where available
    local_stats  = _attach_benchmarks(list(all_local.items())[:10],  "local")
    global_stats = _attach_benchmarks(list(all_global.items())[:10], "global")

    # Step 4 — Rank and select top 5 each
    top_local  = _rank_accounts(local_stats)[:5]
    top_global = _rank_accounts(global_stats)[:5]
    all_ranked = _rank_accounts(local_stats + global_stats)[:10]

    print(f"  [Discovery] Top local:  {[a['handle'] for a in top_local]}")
    print(f"  [Discovery] Top global: {[a['handle'] for a in top_global]}")

    return {
        "local":                    top_local,
        "global":                   top_global,
        "all":                      all_ranked,
        "discovered_at":            datetime.utcnow().isoformat(),
        "total_checked":            len(local_stats) + len(global_stats),
        "benchmarks_last_updated":  BENCHMARKS_LAST_UPDATED,
    }


# ── Step 1: Serper — extract handles + source URLs ───────────────────────────
async def _find_handles_serper(queries: List[str], api_key: str, market: str) -> Dict[str, List]:
    """Returns {handle: [source_dicts]} where source has label + url."""
    handle_sources: Dict[str, List] = {}

    for query in queries[:2]:
        try:
            payload = json.dumps({
                "q":   query,
                "gl":  "sg" if market == "local" else "us",
                "hl":  "en",
                "num": 10,
            }).encode()
            req = urllib.request.Request(
                "https://google.serper.dev/search",
                data=payload,
                headers={"X-API-KEY": api_key, "Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=15) as r:
                data = json.loads(r.read())

            # Extract handles from snippets AND record the source article URL
            for item in data.get("organic", []):
                text    = json.dumps(item)
                found   = re.findall(
                    r'instagram\.com/([a-zA-Z0-9_.]{3,30})(?:/|"|\s|\\)',
                    text
                )
                src_url   = item.get("link", "")
                src_label = item.get("title", src_url)[:50] if item.get("title") else src_url[:50]

                skip = {"p","reel","stories","explore","accounts","instagram",
                        "tv","direct","share","login","signup"}
                for h in found:
                    h = h.lower().strip("_.")
                    if h and h not in skip and len(h) > 2:
                        if h not in handle_sources:
                            handle_sources[h] = []
                        # Only add source if not already recorded
                        existing_urls = [s["url"] for s in handle_sources[h]]
                        if src_url and src_url not in existing_urls:
                            handle_sources[h].append({
                                "label": src_label,
                                "url":   src_url,
                                "via":   "Google search",
                            })

            await asyncio.sleep(0.5)

        except Exception as e:
            print(f"  ⚠ Serper '{query[:40]}': {e}")

    return handle_sources


# ── Step 2: Instagram hashtag scraping ───────────────────────────────────────
async def _find_handles_instagram(hashtags: List[str]) -> Dict[str, List]:
    handle_sources: Dict[str, List] = {}
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-setuid-sandbox", "--disable-dev-shm-usage"]
        )
        ctx = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                       "AppleWebKit/537.36 Chrome/124.0 Safari/537.36",
        )
        page = await ctx.new_page()

        for tag in hashtags:
            ig_url = f"https://www.instagram.com/explore/tags/{tag}/"
            try:
                await page.goto(ig_url, wait_until="networkidle", timeout=25000)
                await page.wait_for_timeout(3000)
                content = await page.content()
                found = re.findall(r'"username"\s*:\s*"([a-zA-Z0-9_.]{3,30})"', content)
                skip = {"instagram", "meta", "facebook"}
                for h in found:
                    h = h.lower()
                    if h not in skip:
                        if h not in handle_sources:
                            handle_sources[h] = []
                        handle_sources[h].append({
                            "label": f"#{tag} on Instagram",
                            "url":   ig_url,
                            "via":   "Instagram hashtag",
                        })
                await asyncio.sleep(2)
            except Exception as e:
                print(f"  ⚠ Instagram #{tag}: {e}")

        await browser.close()
    return handle_sources


# ── Merge handle dicts preserving all sources ─────────────────────────────────
def _merge_handles(*dicts, seeds=None) -> Dict[str, List]:
    merged: Dict[str, List] = {}
    for d in dicts:
        if not isinstance(d, dict):
            continue
        for h, sources in d.items():
            if h not in merged:
                merged[h] = []
            for s in sources:
                if s["url"] not in [x["url"] for x in merged[h]]:
                    merged[h].append(s)
    # Add seeds with no source (already known)
    for h in (seeds or []):
        if h not in merged:
            merged[h] = [{"label": "Known competitor", "url": f"https://instagram.com/{h}", "via": "seed list"}]
    return merged


# ── Step 3: Attach known benchmark data (replaces Social Blade) ──────────────
def _attach_benchmarks(handle_source_pairs: List, market: str) -> List[Dict]:
    """
    Social Blade blocks scrapers, so this uses a manually-maintained benchmark
    table instead. Accounts not in KNOWN_BENCHMARKS still appear, just without
    a follower count — flagged so the dashboard can show "count unknown".
    """
    stats = []
    for handle, sources in handle_source_pairs[:10]:
        bench = KNOWN_BENCHMARKS.get(handle)
        followers   = bench["followers"] if bench else 0
        grade       = bench["grade"] if bench else "—"
        has_data    = bench is not None

        stats.append({
            "handle":            handle,
            "name":              f"@{handle}",
            "market":            market,
            "followers":         followers,
            "growth_30d":        0,  # not available without live scraping
            "grade":             grade,
            "instagram_url":     f"https://www.instagram.com/{handle}/",
            "socialblade_url":   "",  # no longer used
            "website_url":       "",
            "weekly_views":      followers // 10 if followers else 0,
            "discovery_sources": sources[:3],
            "data_known":        has_data,
        })
        if has_data:
            print(f"  ✓ @{handle}: {_fmt(followers)} followers (benchmark) | Grade: {grade}")
        else:
            print(f"  • @{handle}: discovered, follower count unknown")

    return stats


# ── Step 4: Rank — known followers first, then discovered-but-unknown ────────
def _rank_accounts(accounts: List[Dict]) -> List[Dict]:
    for a in accounts:
        f = a.get("followers", 0)
        a["discovery_score"] = f
    # Known-data accounts ranked by followers; unknown accounts kept after, in discovery order
    known   = [a for a in accounts if a.get("data_known")]
    unknown = [a for a in accounts if not a.get("data_known")]
    known.sort(key=lambda x: x["discovery_score"], reverse=True)
    return known + unknown


# ── Helpers ───────────────────────────────────────────────────────────────────
def _fmt(n: int) -> str:
    if abs(n) >= 1_000_000: return f"{n/1_000_000:.1f}M"
    if abs(n) >= 1_000:     return f"{n/1_000:.1f}K"
    return str(n)
