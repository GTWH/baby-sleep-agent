"""
scrapers/blogs.py
Scrapes top blog articles using Google Custom Search API.
Free tier: 100 queries/day — more than enough for weekly runs.

Setup (5 minutes, free):
  1. Go to console.cloud.google.com → Enable "Custom Search API"
  2. Get API key: APIs & Services → Credentials → Create API Key
  3. Create Search Engine: cse.google.com/cse/create/new
     - In "Sites to search": leave blank then set to "Search the entire web"
     - Copy the Search Engine ID (cx)
  4. Add to GitHub Secrets: GOOGLE_API_KEY and GOOGLE_CSE_ID
"""

import asyncio
import urllib.request
import urllib.parse
import json
from datetime import datetime, timedelta


async def scrape_blogs(keywords: list, api_key: str, cse_id: str) -> list:
    posts = []
    # Date filter: past 7 days
    since = (datetime.now() - timedelta(days=7)).strftime("%Y%m%d")

    for kw in keywords[:4]:               # 4 keywords × 1 query = 4 of 100 free daily quota
        try:
            params = urllib.parse.urlencode({
                "key":          api_key,
                "cx":           cse_id,
                "q":            kw,
                "num":          10,
                "dateRestrict": "w1",      # past week
                "sort":         "date",
            })
            url = f"https://www.googleapis.com/customsearch/v1?{params}"

            req = urllib.request.Request(url, headers={"Accept": "application/json"})
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read())

            for item in data.get("items", []):
                posts.append({
                    "source":      "blog",
                    "id":          item.get("link", ""),
                    "title":       item.get("title", ""),
                    "url":         item.get("link", ""),
                    "author":      item.get("displayLink", ""),
                    "description": item.get("snippet", ""),
                    "views":       0,
                    "likes":       0,
                    "saves":       0,
                    "published_at": item.get("pagemap", {})
                                       .get("metatags", [{}])[0]
                                       .get("article:published_time", ""),
                })

            await asyncio.sleep(0.5)

        except Exception as e:
            print(f"    ⚠ Blog search '{kw}': {e}")

    print(f"    Blogs → {len(posts)} articles via Google Custom Search")
    return posts
