"""
Baby Sleep Content Agent — FREE STACK VERSION
mybelovedsleep.com

Sources:
  - Instagram  → Playwright (public hashtag pages, no API key)
  - TikTok     → Playwright (public search pages, no API key)
  - Pinterest  → Playwright + RSS (public, no API key)
  - Blogs      → Google Custom Search API (free: 100 queries/day)
  - Competitors→ Playwright (public pages, no API key)

AI: Google Gemini 1.5 Flash (free: 1,500 requests/day)

Cost: $0.00/month
Runs: Every Monday 6am SGT via GitHub Actions (free)
"""

import asyncio
import json
import os
from datetime import datetime
from pathlib import Path

from scrapers.instagram  import scrape_instagram
from scrapers.tiktok     import scrape_tiktok
from scrapers.pinterest  import scrape_pinterest
from scrapers.blogs      import scrape_blogs
from scrapers.competitors import scrape_competitors
from ai.viral_scorer     import rank_posts
from ai.content_gen      import generate_weekly_content
from ai.gap_analysis     import run_gap_analysis
from output.reporter     import build_dashboard_json

# ── Config ───────────────────────────────────────────────────────────────────
HASHTAGS = [
    "babysleep", "sleeptraining", "sleepregression",
    "babysleeptips", "newbornsleep", "gentlesleeptraining",
    "babysleepcoach", "4monthsleepregression",
]

KEYWORDS = [
    "baby sleep consulting",
    "baby sleep training",
    "sleep regression baby",
    "newborn sleep schedule",
    "gentle sleep training",
]

COMPETITORS = [
    {"name": "Little Z's Sleep",       "url": "https://littlezssleep.com/blog"},
    {"name": "Precious Little Sleep",  "url": "https://preciouslittlesleep.com/blog"},
    {"name": "Taking Cara Babies",     "url": "https://takingcarababies.com/blog"},
    {"name": "The Sleep Lady",         "url": "https://sleeplady.com/baby-sleep"},
    {"name": "Baby Sleep Science",     "url": "https://babysleepscience.com/blog"},
]

BRAND = {
    "name":   "My Beloved Sleep",
    "handle": "@mybelovedsleep",
    "url":    "https://www.mybelovedsleep.com",
    "tone":   "warm, expert, empathetic, Singapore-based, science-backed",
    "market": "Singapore and Southeast Asia",
    "cta":    "Book a free 15-minute discovery call at mybelovedsleep.com",
}


async def run_agent():
    print(f"\n{'='*60}")
    print(f"  Baby Sleep Agent (FREE STACK) — {datetime.now().strftime('%Y-%m-%d %H:%M')} SGT")
    print(f"{'='*60}\n")

    # Step 1 — Scrape all sources in parallel
    print("[1/5] Scraping all sources with Playwright + Google Search...")
    results = await asyncio.gather(
        scrape_instagram(HASHTAGS),
        scrape_tiktok(KEYWORDS),
        scrape_pinterest(KEYWORDS),
        scrape_blogs(KEYWORDS, api_key=os.environ["GOOGLE_API_KEY"],
                     cse_id=os.environ["GOOGLE_CSE_ID"]),
        scrape_competitors(COMPETITORS),
    )

    ig_posts, tt_posts, pin_posts, blog_posts, comp_data = results
    all_posts = ig_posts + tt_posts + pin_posts + blog_posts

    print(f"    ✓ Instagram : {len(ig_posts)} posts")
    print(f"    ✓ TikTok    : {len(tt_posts)} posts")
    print(f"    ✓ Pinterest : {len(pin_posts)} pins")
    print(f"    ✓ Blogs     : {len(blog_posts)} articles")
    print(f"    ✓ Competitors: {len(comp_data)} sites scraped")
    print(f"    ✓ Total     : {len(all_posts)} items collected")

    # Step 2 — Score & rank
    print("\n[2/5] Scoring viral posts...")
    ranked = rank_posts(all_posts, top_n=10)
    print(f"    ✓ {len(ranked)} viral posts ranked")

    # Step 3 — Generate content with Gemini
    print("\n[3/5] Generating adapted content with Gemini AI...")
    content = await generate_weekly_content(
        viral_posts=ranked[:3],
        brand=BRAND,
        gemini_api_key=os.environ["GEMINI_API_KEY"],
    )
    print("    ✓ Blog template, IG carousel, reel script generated")

    # Step 4 — Gap analysis with Gemini
    print("\n[4/5] Running competitor gap analysis...")
    gaps = await run_gap_analysis(
        competitor_data=comp_data,
        gemini_api_key=os.environ["GEMINI_API_KEY"],
    )
    print(f"    ✓ {len(gaps)} gaps identified")

    # Step 5 — Build & save dashboard JSON
    print("\n[5/5] Building dashboard report...")
    report = build_dashboard_json(
        viral_posts=ranked,
        content=content,
        gaps=gaps,
        competitor_data=comp_data,
        run_date=datetime.now().isoformat(),
    )

    out_dir = Path("dashboard")
    out_dir.mkdir(exist_ok=True)
    (out_dir / "report_latest.json").write_text(json.dumps(report, indent=2))
    (out_dir / f"report_{datetime.now().strftime('%Y-%m-%d')}.json").write_text(
        json.dumps(report, indent=2)
    )

    print(f"\n{'='*60}")
    print(f"  ✅ Done!  {len(all_posts)} posts → {len(ranked)} viral hits")
    print(f"  💰 Cost this run: $0.00")
    print(f"  📊 dashboard/report_latest.json updated")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    asyncio.run(run_agent())
