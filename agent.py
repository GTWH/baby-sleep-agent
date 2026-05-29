"""
Baby Sleep Content Agent — FREE STACK VERSION
mybelovedsleep.com

Sources:
  - Instagram  → Playwright (public hashtag pages)
  - TikTok     → Playwright (public search pages)
  - Pinterest  → Playwright (public search pages)
  - Blogs      → Serper.dev (free: 2,500 searches/month)
  - Competitors→ Playwright (public blog pages)

AI: Google Gemini 2.0 Flash (free: 1,500 requests/day)
    With escalating retry (60s→120s→180s→240s) + graceful fallback tracking

Cost: $0.00/month
Runs: Every Monday 6am SGT via GitHub Actions (free)
"""

import asyncio
import json
import os
from datetime import datetime
from pathlib import Path

from scrapers.instagram   import scrape_instagram
from scrapers.tiktok      import scrape_tiktok
from scrapers.pinterest   import scrape_pinterest
from scrapers.blogs       import scrape_blogs
from scrapers.competitors import scrape_competitors
from ai.viral_scorer      import rank_posts
from ai.content_gen       import generate_weekly_content
from ai.gap_analysis      import run_gap_analysis
from output.reporter      import build_dashboard_json

# ── Config ────────────────────────────────────────────────────────────────────
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
    run_start = datetime.utcnow()
    reliability_log = []   # collects status from every Gemini call this run

    print(f"\n{'='*60}")
    print(f"  Baby Sleep Agent (FREE) — {datetime.now().strftime('%Y-%m-%d %H:%M')} SGT")
    print(f"{'='*60}\n")

    # ── Step 1: Scrape all sources ────────────────────────────────────────
    print("[1/5] Scraping all sources...")
    results = await asyncio.gather(
        scrape_instagram(HASHTAGS),
        scrape_tiktok(KEYWORDS),
        scrape_pinterest(KEYWORDS),
        scrape_blogs(KEYWORDS, serper_api_key=os.environ["SERPER_API_KEY"]),
        scrape_competitors(COMPETITORS),
    )

    ig_posts, tt_posts, pin_posts, blog_posts, comp_data = results
    all_posts = ig_posts + tt_posts + pin_posts + blog_posts

    print(f"    ✓ Instagram  : {len(ig_posts)} posts")
    print(f"    ✓ TikTok     : {len(tt_posts)} posts")
    print(f"    ✓ Pinterest  : {len(pin_posts)} pins")
    print(f"    ✓ Blogs      : {len(blog_posts)} articles")
    print(f"    ✓ Competitors: {len(comp_data)} sites")
    print(f"    ✓ Total      : {len(all_posts)} items collected")

    # ── Step 2: Score & rank ──────────────────────────────────────────────
    print("\n[2/5] Scoring viral posts...")
    ranked = rank_posts(all_posts, top_n=10)
    print(f"    ✓ {len(ranked)} viral posts ranked")

    # ── Step 3: Generate content (tracks reliability) ─────────────────────
    print("\n[3/5] Generating adapted content with Gemini AI...")
    content = await generate_weekly_content(
        viral_posts=ranked[:3],
        brand=BRAND,
        gemini_api_key=os.environ["GEMINI_API_KEY"],
    )
    # Collect reliability data from content generation
    if "reliability" in content:
        reliability_log.extend(content["reliability"]["details"])
        _print_reliability_summary("Content generation", content["reliability"])

    # ── Step 4: Gap analysis (tracks reliability) ─────────────────────────
    print("\n[4/5] Running competitor gap analysis...")
    gaps, gap_status = await run_gap_analysis(
        competitor_data=comp_data,
        gemini_api_key=os.environ["GEMINI_API_KEY"],
    )
    reliability_log.append(gap_status)
    _print_reliability_summary("Gap analysis", {
        "calls_total": 1,
        "calls_success": 1 if gap_status["result"] == "success" else 0,
        "calls_fallback": 1 if gap_status["result"] == "fallback" else 0,
        "fallback_rate": "0%" if gap_status["result"] == "success" else "100%",
        "details": [gap_status],
    })

    # ── Step 5: Build & save dashboard JSON ───────────────────────────────
    print("\n[5/5] Building dashboard report...")

    # Summarise reliability across ALL 4 Gemini calls this run
    total_calls    = len(reliability_log)
    total_fallback = sum(1 for s in reliability_log if s["result"] == "fallback")
    total_success  = total_calls - total_fallback
    run_reliability = {
        "run_date":         run_start.isoformat(),
        "calls_total":      total_calls,
        "calls_success":    total_success,
        "calls_fallback":   total_fallback,
        "fallback_rate":    f"{round(total_fallback / max(total_calls,1) * 100)}%",
        "run_complete":     total_fallback == 0,
        "details":          reliability_log,
    }

    report = build_dashboard_json(
        viral_posts=ranked,
        content=content,
        gaps=gaps,
        competitor_data=comp_data,
        run_date=run_start.isoformat(),
        reliability=run_reliability,
    )

    # Save latest report
    out_dir = Path("docs")
    out_dir.mkdir(exist_ok=True)
    (out_dir / "report_latest.json").write_text(json.dumps(report, indent=2))
    (out_dir / f"report_{run_start.strftime('%Y-%m-%d')}.json").write_text(
        json.dumps(report, indent=2)
    )

    # ── Append to reliability history log ─────────────────────────────────
    history_path = Path("docs/reliability_history.json")
    history = []
    if history_path.exists():
        try:
            history = json.loads(history_path.read_text())
        except Exception:
            history = []
    history.append(run_reliability)
    history_path.write_text(json.dumps(history, indent=2))

    # ── Final summary ─────────────────────────────────────────────────────
    run_mins = round((datetime.utcnow() - run_start).seconds / 60, 1)
    print(f"\n{'='*60}")
    print(f"  ✅ Run complete in {run_mins} min")
    print(f"  🤖 Gemini: {total_success}/{total_calls} calls succeeded  |  {total_fallback} fallback(s)")
    if total_fallback > 0:
        print(f"  ⚠  {total_fallback} section(s) used placeholder text — re-run to regenerate")
    print(f"  📊 dashboard/report_latest.json updated")
    print(f"  📈 dashboard/reliability_history.json updated ({len(history)} runs tracked)")
    print(f"{'='*60}\n")


def _print_reliability_summary(label: str, rel: dict):
    icon = "✓" if rel["calls_fallback"] == 0 else "⚠"
    print(f"    {icon} {label}: {rel['calls_success']}/{rel['calls_total']} succeeded, "
          f"{rel['calls_fallback']} fallback(s) [{rel['fallback_rate']}]")


if __name__ == "__main__":
    asyncio.run(run_agent())
