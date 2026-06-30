"""
scrapers/youtube.py
Finds viral baby sleep videos using the official YouTube Data API v3 (free tier).

WHY THE OFFICIAL API INSTEAD OF SCRAPING:
  - Real view/like/comment counts, not estimates
  - Never gets blocked like Instagram/TikTok/Social Blade
  - Free tier: 10,000 units/day. A search.list call costs 100 units,
    so this uses ~1,000 units per run (10 searches) — well within budget.

SETUP (10 minutes, free, no billing required for free quota):
  1. Go to console.cloud.google.com → create a project
  2. APIs & Services → Library → enable "YouTube Data API v3"
  3. APIs & Services → Credentials → Create API key
  4. Add to GitHub Secrets as: YOUTUBE_API_KEY

NOTE: There is no "trending in this niche" endpoint on YouTube's API —
only global Trending (not niche-specific) or keyword search. This searches
for baby-sleep-related keywords and sorts by view count, which is the
closest free equivalent to "what's viral in this topic right now."
"""

import asyncio
import json
import urllib.request
import urllib.parse
from typing import List, Dict


YOUTUBE_SEARCH_URL = "https://www.googleapis.com/youtube/v3/search"
YOUTUBE_VIDEOS_URL = "https://www.googleapis.com/youtube/v3/videos"

SEARCH_KEYWORDS = [
    "baby sleep regression",
    "baby sleep training",
    "newborn sleep schedule",
    "gentle sleep training baby",
    "4 month sleep regression",
    "sleep consultant",
    "evidence-based sleep training",
    "how to sleep train",
    "sleep regression",
    "baby not sleeping",
]


async def scrape_youtube(youtube_api_key: str = "") -> List[Dict]:
    """
    Searches YouTube for baby-sleep-related videos published in the last
    month, sorted by view count. Uses ~10 search calls + 1 batched stats
    call per run (~1,000 units total, well under the 10,000/day free quota).
    """
    if not youtube_api_key:
        print("    ⚠ YouTube: no API key provided, skipping")
        return []

    all_video_ids = []
    video_meta = {}

    for kw in SEARCH_KEYWORDS:
        try:
            ids, meta = await asyncio.to_thread(_search_youtube, kw, youtube_api_key)
            all_video_ids.extend(ids)
            video_meta.update(meta)
            await asyncio.sleep(0.3)
        except Exception as e:
            print(f"    ⚠ YouTube search '{kw}': {e}")
            continue

    # Deduplicate video IDs
    unique_ids = list(dict.fromkeys(all_video_ids))[:50]  # cap to keep stats call light

    if not unique_ids:
        print("    YouTube → 0 videos found")
        return []

    try:
        stats = await asyncio.to_thread(_get_video_stats, unique_ids, youtube_api_key)
    except Exception as e:
        print(f"    ⚠ YouTube stats lookup: {e}")
        return []

    posts = []
    for vid_id, stat in stats.items():
        meta = video_meta.get(vid_id, {})
        views    = stat.get("viewCount", 0)
        likes    = stat.get("likeCount", 0)
        comments = stat.get("commentCount", 0)

        posts.append({
            "source":             "youtube",
            "id":                 vid_id,
            "title":              meta.get("title", "")[:150],
            "url":                f"https://www.youtube.com/watch?v={vid_id}",
            "author":             meta.get("channel", ""),
            "description":        meta.get("description", "")[:200],
            "views":              views,
            "likes":              likes,
            "saves":              0,
            "comments":           comments,
            "published_at":       meta.get("published_at", ""),
            "engagement_summary": f"{_fmt(views)} views · {_fmt(likes)} likes",
        })

    posts.sort(key=lambda p: p["views"], reverse=True)
    print(f"    YouTube → {len(posts)} videos via YouTube Data API")
    return posts[:15]


def _search_youtube(keyword: str, api_key: str) -> tuple:
    """Single search call — returns (video_ids, {id: meta_dict})."""
    params = {
        "part":       "snippet",
        "q":          f"{keyword} baby",
        "type":       "video",
        "order":      "viewCount",
        "maxResults": 10,
        "publishedAfter": _one_month_ago_iso(),
        "key":        api_key,
    }
    url = f"{YOUTUBE_SEARCH_URL}?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(url, method="GET")

    with urllib.request.urlopen(req, timeout=15) as r:
        data = json.loads(r.read())

    ids  = []
    meta = {}
    for item in data.get("items", []):
        vid_id = item.get("id", {}).get("videoId")
        if not vid_id:
            continue
        snippet = item.get("snippet", {})
        ids.append(vid_id)
        meta[vid_id] = {
            "title":        snippet.get("title", ""),
            "channel":      snippet.get("channelTitle", ""),
            "description":  snippet.get("description", ""),
            "published_at": snippet.get("publishedAt", ""),
        }
    return ids, meta


def _get_video_stats(video_ids: List[str], api_key: str) -> Dict[str, Dict]:
    """Batched call — gets view/like/comment counts for up to 50 video IDs at once."""
    params = {
        "part": "statistics",
        "id":   ",".join(video_ids),
        "key":  api_key,
    }
    url = f"{YOUTUBE_VIDEOS_URL}?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(url, method="GET")

    with urllib.request.urlopen(req, timeout=15) as r:
        data = json.loads(r.read())

    stats = {}
    for item in data.get("items", []):
        vid_id = item.get("id")
        s = item.get("statistics", {})
        stats[vid_id] = {
            "viewCount":    int(s.get("viewCount", 0)),
            "likeCount":    int(s.get("likeCount", 0)),
            "commentCount": int(s.get("commentCount", 0)),
        }
    return stats


def _one_month_ago_iso() -> str:
    from datetime import datetime, timedelta
    return (datetime.utcnow() - timedelta(days=30)).strftime("%Y-%m-%dT%H:%M:%SZ")


def _fmt(n: int) -> str:
    if n >= 1_000_000: return f"{n/1_000_000:.1f}M"
    if n >= 1_000:     return f"{n/1_000:.1f}K"
    return str(n)
