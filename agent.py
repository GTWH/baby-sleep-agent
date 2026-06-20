"""
Baby Sleep Content Agent — FREE STACK VERSION
mybelovedsleep.com

Sources:
  - Instagram  → Playwright (public hashtag pages)
  - TikTok     → Playwright (public search pages)
  - Pinterest  → Playwright (public search pages)
  - Blogs      → Serper.dev (free: 2,500 searches/month)
  - Competitors→ Auto-discovered weekly via Serper + Instagram + Social Blade

AI: Google Gemini 2.5 Flash-Lite (free)
Cost: $0.00/month · Runs: Every Monday 6am SGT via GitHub Actions
"""

import asyncio
import json
import os
from datetime import datetime
from pathlib import Path

from scrapers.instagram          import scrape_instagram
from scrapers.tiktok             import scrape_tiktok
from scrapers.pinterest          import scrape_pinterest
from scrapers.blogs              import scrape_blogs
from scrapers.competitor_discovery import discover_competitors
from ai.viral_scorer             import rank_posts
from ai.content_gen              import generate_weekly_content
from ai.gap_analysis             import run_gap_analysis
from output.reporter             import build_dashboard_json

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

BRAND = {
    "name":   "My Beloved Sleep",
    "handle": "@mybelovedsleep",
    "url":    "https://www.mybelovedsleep.com",
    "tone":   "warm, expert, empathetic, Singapore-based, science-backed",
    "market": "Singapore and Southeast Asia",
    "cta":    "Book a free 15-minute discovery call at mybelovedsleep.com",
}


async def run_agent():
    run_start        = datetime.utcnow()
    reliability_log  = []

    print(f"\n{'='*60}")
    print(f"  Baby Sleep Agent (FREE) — {datetime.now().strftime('%Y-%m-%d %H:%M')} SGT")
    print(f"{'='*60}\n")

    # ── Step 1: Auto-discover competitors ─────────────────────────────────────
    print("[1/6] Auto-discovering top baby sleep accounts (SG + Global)...")
    competitor_data = await discover_competitors(
        serper_api_key=os.environ["SERPER_API_KEY"],
    )
    top_competitors = competitor_data.get("all", [])
    print(f"    ✓ {len(top_competitors)} competitors discovered and ranked")
    print(f"    ✓ Local top: {[a['handle'] for a in competitor_data.get('local', [])]}")
    print(f"    ✓ Global top: {[a['handle'] for a in competitor_data.get('global', [])]}")

    # ── Step 2: Scrape content sources in parallel ─────────────────────────────
    print("\n[2/6] Scraping content sources...")
    results = await asyncio.gather(
        scrape_instagram(HASHTAGS),
        scrape_tiktok(KEYWORDS),
        scrape_pinterest(KEYWORDS),
        scrape_blogs(KEYWORDS, serper_api_key=os.environ["SERPER_API_KEY"]),
    )

    ig_posts, tt_posts, pin_posts, blog_posts = results
    all_posts = ig_posts + tt_posts + pin_posts + blog_posts

    print(f"    ✓ Instagram  : {len(ig_posts)} posts")
    print(f"    ✓ TikTok     : {len(tt_posts)} posts")
    print(f"    ✓ Pinterest  : {len(pin_posts)} pins")
    print(f"    ✓ Blogs      : {len(blog_posts)} articles")
    print(f"    ✓ Total      : {len(all_posts)} items")

    # ── Step 3: Score & rank viral posts ──────────────────────────────────────
    print("\n[3/6] Scoring viral posts...")
    ranked = rank_posts(all_posts, top_n=10)
    print(f"    ✓ {len(ranked)} viral posts ranked")

    # ── Step 4: Generate AI content ────────────────────────────────────────────
    print("\n[4/6] Generating adapted content with Gemini AI...")
    content = await generate_weekly_content(
        viral_posts=ranked[:3],
        brand=BRAND,
        gemini_api_key=os.environ["GEMINI_API_KEY"],
    )
    if "reliability" in content:
        reliability_log.extend(content["reliability"]["details"])
        _print_rel("Content generation", content["reliability"])

    # ── Step 5: Gap analysis ──────────────────────────────────────────────────
    print("\n[5/6] Running competitor gap analysis...")
    gaps, gap_status = await run_gap_analysis(
        competitor_data=top_competitors,
        gemini_api_key=os.environ["GEMINI_API_KEY"],
    )
    reliability_log.append(gap_status)
    _print_rel("Gap analysis", {
        "calls_total": 1, "calls_fallback": 1 if gap_status["result"]=="fallback" else 0,
        "calls_success": 1 if gap_status["result"]=="success" else 0,
        "fallback_rate": "0%" if gap_status["result"]=="success" else "100%",
    })

    # ── Step 6: Build & save dashboard JSON ───────────────────────────────────
    print("\n[6/6] Building dashboard report...")
    total_calls    = len(reliability_log)
    total_fallback = sum(1 for s in reliability_log if s["result"] == "fallback")
    run_reliability = {
        "run_date":       run_start.isoformat(),
        "calls_total":    total_calls,
        "calls_success":  total_calls - total_fallback,
        "calls_fallback": total_fallback,
        "fallback_rate":  f"{round(total_fallback/max(total_calls,1)*100)}%",
        "run_complete":   total_fallback == 0,
        "details":        reliability_log,
    }

    report = build_dashboard_json(
        viral_posts=ranked,
        content=content,
        gaps=gaps,
        competitor_data=top_competitors,
        competitor_discovery=competitor_data,
        run_date=run_start.isoformat(),
        reliability=run_reliability,
    )

    out_dir = Path("docs")
    out_dir.mkdir(exist_ok=True)
    (out_dir / "report_latest.json").write_text(json.dumps(report, indent=2))
    (out_dir / f"report_{run_start.strftime('%Y-%m-%d')}.json").write_text(
        json.dumps(report, indent=2)
    )

    # Append to reliability history
    history_path = Path("docs/reliability_history.json")
    history = []
    if history_path.exists():
        try: history = json.loads(history_path.read_text())
        except: history = []
    history.append(run_reliability)
    history_path.write_text(json.dumps(history, indent=2))

    # Save competitor discovery history
    comp_history_path = Path("docs/competitor_history.json")
    comp_history = []
    if comp_history_path.exists():
        try: comp_history = json.loads(comp_history_path.read_text())
        except: comp_history = []
    comp_history.append({
        "week": run_start.strftime("%Y-%m-%d"),
        "local":  [a["handle"] for a in competitor_data.get("local", [])],
        "global": [a["handle"] for a in competitor_data.get("global", [])],
    })
    comp_history_path.write_text(json.dumps(comp_history, indent=2))

    run_mins = round((datetime.utcnow() - run_start).seconds / 60, 1)
    print(f"\n{'='*60}")
    print(f"  ✅ Run complete in {run_mins} min")
    print(f"  🔍 Competitors: {len(top_competitors)} discovered")
    print(f"  🤖 Gemini: {total_calls - total_fallback}/{total_calls} calls succeeded")
    print(f"  💰 Cost: $0.00")
    print(f"  📊 docs/report_latest.json updated")
    print(f"{'='*60}\n")


def _print_rel(label, rel):
    icon = "✓" if rel.get("calls_fallback", 0) == 0 else "⚠"
    print(f"    {icon} {label}: {rel.get('calls_success',0)}/{rel.get('calls_total',0)} succeeded")


if __name__ == "__main__":
    asyncio.run(run_agent())
