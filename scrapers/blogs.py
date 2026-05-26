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


def _domain(url: str) -> str:
    try:
        m = re.search(r"https?://(?:www\.)?([^/]+)", url)
        return m.group(1) if m else url
    except Exception:
        return url
