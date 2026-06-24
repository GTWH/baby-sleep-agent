"""
scrapers/blogs.py
Finds top blog articles using Serper.dev — Google Search API.

WHY SERPER.DEV INSTEAD OF SCRAPING:
  - Never breaks — uses Google's own index, no HTML scraping
  - Free tier: 2,500 searches/month (your weekly runs use ~20/month)
  - No credit card needed to sign up
  - Stable JSON API — extremely unlikely to change

SETUP (2 minutes, free):
  1. Go to serper.dev
  2. Click "Get Started Free" — sign in with Google
  3. Copy your API key from the dashboard
  4. Add to GitHub Secrets as: SERPER_API_KEY
"""

import asyncio
import json
import urllib.request
import urllib.parse
import re
from typing import List, Dict


SERPER_URL = "https://google.serper.dev/search"

# Trending topic search queries — rotates weekly by index
TRENDING_QUERIES = [
    "baby sleep tips viral 2026",
    "sleep regression baby what to do",
    "how to get baby to sleep through the night",
    "newborn wake windows schedule",
    "overtired baby signs and solutions",
    "how to drop night feed baby",
    "4 month sleep regression help",
    "baby sleep training methods comparison",
    "gentle sleep training newborn",
    "baby nap schedule by age",
]


async def scrape_blogs(keywords: List[str], serper_api_key: str = "") -> List[Dict]:
    """
    Search for top blog articles published in the past week.
    Uses ~4 API calls per run (well within 2,500/month free limit).
    """
    posts = []

    for kw in keywords[:4]:        # 4 keywords = 4 of your 2,500 monthly quota
        try:
            result = await asyncio.to_thread(
                _search_serper, kw, serper_api_key
            )
            posts.extend(result)
            await asyncio.sleep(0.5)   # gentle delay between calls

        except Exception as e:
            print(f"    ⚠ Blog search '{kw}': {e}")
            continue

    # Deduplicate by URL
    seen = set()
    unique = []
    for p in posts:
        if p["url"] not in seen:
            seen.add(p["url"])
            unique.append(p)

    print(f"    Blogs → {len(unique)} articles via Serper.dev")
    return unique


async def get_trending_topics(serper_api_key: str, week_index: int = 0) -> List[Dict]:
    """
    Finds genuinely trending baby sleep topics this week via Google search.
    Uses 2 Serper calls per run. Returns posts shaped the same as other scrapers
    so they slot straight into viral_posts without any changes upstream.

    week_index: pass the current ISO week number so queries rotate each week.
    """
    topics = []

    # Pick 2 queries based on current week so it varies each run
    q1 = TRENDING_QUERIES[week_index % len(TRENDING_QUERIES)]
    q2 = TRENDING_QUERIES[(week_index + 1) % len(TRENDING_QUERIES)]

    for query in [q1, q2]:
        try:
            result = await asyncio.to_thread(
                _search_serper_trending, query, serper_api_key
            )
            topics.extend(result)
            await asyncio.sleep(0.5)
        except Exception as e:
            print(f"    ⚠ Trending search '{query}': {e}")
            continue

    # Deduplicate by URL
    seen = set()
    unique = []
    for t in topics:
        if t["url"] not in seen:
            seen.add(t["url"])
            unique.append(t)

    print(f"    Trending topics → {len(unique)} results via Serper.dev")
    return unique


def _search_serper(keyword: str, api_key: str) -> List[Dict]:
    """Single synchronous Serper.dev search call."""
    payload = json.dumps({
        "q":          f"{keyword} baby sleep",
        "gl":         "sg",        # Singapore region results
        "hl":         "en",
        "num":        10,
        "tbs":        "qdr:w",     # past week only
    }).encode("utf-8")

    req = urllib.request.Request(
        SERPER_URL,
        data=payload,
        headers={
            "X-API-KEY":    api_key,
            "Content-Type": "application/json",
        },
        method="POST",
    )

    with urllib.request.urlopen(req, timeout=15) as resp:
        data = json.loads(resp.read())

    posts = []
    for item in data.get("organic", []):
        posts.append({
            "source":       "blog",
            "id":           item.get("link", ""),
            "title":        item.get("title", "")[:150],
            "url":          item.get("link", ""),
            "author":       _domain(item.get("link", "")),
            "description":  item.get("snippet", ""),
            "views":        0,
            "likes":        0,
            "saves":        0,
            "published_at": item.get("date", ""),
        })
    return posts


def _search_serper_trending(query: str, api_key: str) -> List[Dict]:
    """
    Serper search tuned for trending topics — broader date range,
    sorted by relevance, pulls title + snippet as the topic signal.
    """
    payload = json.dumps({
        "q":   query,
        "gl":  "us",       # US gives more volume for global trending signal
        "hl":  "en",
        "num": 10,
        "tbs": "qdr:w",    # past week
    }).encode("utf-8")

    req = urllib.request.Request(
        SERPER_URL,
        data=payload,
        headers={
            "X-API-KEY":    api_key,
            "Content-Type": "application/json",
        },
        method="POST",
    )

    with urllib.request.urlopen(req, timeout=15) as resp:
        data = json.loads(resp.read())

    posts = []
    for item in data.get("organic", []):
        title = item.get("title", "")[:150]
        snippet = item.get("snippet", "")
        if not title:
            continue
        posts.append({
            "source":             "trending_search",
            "id":                 item.get("link", ""),
            "title":              title,
            "url":                item.get("link", ""),
            "author":             _domain(item.get("link", "")),
            "description":        snippet,
            "engagement_summary": snippet[:120],
            "views":              500,   # nominal score so ranker includes it
            "likes":              50,
            "saves":              20,
            "published_at":       item.get("date", ""),
            "viral_score":        60,    # baseline so it competes with scraped posts
        })
    return posts


def _domain(url: str) -> str:
    try:
        m = re.search(r"https?://(?:www\.)?([^/]+)", url)
        return m.group(1) if m else url
    except Exception:
        return url
