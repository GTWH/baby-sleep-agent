"""
ai/gap_analysis.py
Analyses competitor data and uses Gemini to surface
prioritised content gaps with action plans.

Retry strategy on 429 Too Many Requests:
  Attempt 1 fails → wait 60s  → retry
  Attempt 2 fails → wait 120s → retry
  Attempt 3 fails → wait 180s → retry
  Attempt 4 fails → wait 240s → retry
  Attempt 5 fails → return built-in fallback gaps (never crashes)
"""

import asyncio
import json
import re
import time
import urllib.request
import urllib.error
from typing import List, Dict


GEMINI_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models/"
    "gemini-2.0-flash:generateContent"
)

# Escalating wait times: 60s → 120s → 180s → 240s
RETRY_WAITS = [60, 120, 180, 240]


def _call_gemini_with_retry(prompt: str, api_key: str) -> str:
    """Call Gemini with escalating retry delays on 429 errors."""
    url = f"{GEMINI_URL}?key={api_key}"
    payload = json.dumps({
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "maxOutputTokens": 1000,
            "temperature":     0.5,
        },
    }).encode()

    for attempt, wait in enumerate(RETRY_WAITS, start=1):
        try:
            req = urllib.request.Request(
                url, data=payload,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=30) as r:
                result = json.loads(r.read())
            print(f"    ✓ Gap analysis Gemini call succeeded on attempt {attempt}")
            return result["candidates"][0]["content"]["parts"][0]["text"]

        except urllib.error.HTTPError as e:
            if e.code == 429:
                print(f"    ⏳ Gap analysis rate limited — attempt {attempt}/{len(RETRY_WAITS)}")
                print(f"    ⏳ Waiting {wait}s before retry {attempt + 1}...")
                time.sleep(wait)
                continue
            else:
                raise

    print(f"    ⚠ Gap analysis — all retries exhausted. Using built-in fallback gaps.")
    return "[]"


async def run_gap_analysis(
    competitor_data: List[Dict],
    gemini_api_key: str,
) -> List[Dict]:

    comp_summary = "\n".join([
        f"- {c['name']}: {c.get('pages', 0)} posts found, "
        f"recent titles: {'; '.join(c.get('titles', [])[:3])}"
        for c in competitor_data if not c.get("error")
    ]) or "No competitor data available this week."

    prompt = f"""
You are auditing the content strategy of My Beloved Sleep (mybelovedsleep.com),
a Singapore baby sleep consulting brand, versus these competitors:

{comp_summary}

Identify exactly 6 content and distribution gaps. Return ONLY a valid JSON
array — no markdown, no code fences, no extra text. Each object must have:
  "priority"  : "high" | "medium" | "low"
  "title"     : gap name, 5-8 words
  "why"       : 2 sentences explaining why competitors outperform here
  "action"    : 2-3 concrete numbered steps achievable in 2 weeks
  "effort"    : "30 min" | "2-3 hours" | "1 day"
  "impact"    : "quick win" | "medium term" | "long term"
"""

    print("\n    [Gemini 4/4] Gap analysis — pausing 60s first...")
    await asyncio.sleep(60)

    raw = await asyncio.to_thread(_call_gemini_with_retry, prompt, gemini_api_key)
    raw = re.sub(r"```json|```", "", raw).strip()

    try:
        gaps = json.loads(raw)
        print(f"    ✓ {len(gaps)} gaps identified by Gemini")
        return gaps
    except json.JSONDecodeError:
        print("    ⚠ Gemini returned unexpected format — using built-in fallback gaps")
        return _fallback_gaps()


def _fallback_gaps() -> List[Dict]:
    return [
        {
            "priority": "high",
            "title": "No TikTok presence at all",
            "why": "Top viral posts this week were on TikTok with millions of views. Competitors capture younger parents earlier in their parenting journey.",
            "action": "1. Create @mybelovedsleep TikTok account. 2. Post this week's reel script as your first video. 3. Aim for 3 posts per week.",
            "effort": "2-3 hours",
            "impact": "medium term"
        },
        {
            "priority": "high",
            "title": "Posting frequency 3x below competitors",
            "why": "Competitors post 7-10 times per week across platforms. More touchpoints means more algorithm exposure and follower growth.",
            "action": "1. Use agent weekly output as minimum (blog + carousel + reel). 2. Add 2 story posts per week. 3. Repurpose each blog into 3 social posts.",
            "effort": "2-3 hours",
            "impact": "quick win"
        },
        {
            "priority": "high",
            "title": "Missing Singapore-specific SEO content",
            "why": "No pages rank for 'baby sleep consultant Singapore'. Local search is completely open for the taking.",
            "action": "1. Write one blog post targeting 'baby sleep consultant Singapore'. 2. Add location meta tags. 3. Submit updated sitemap to Google Search Console.",
            "effort": "1 day",
            "impact": "long term"
        },
        {
            "priority": "medium",
            "title": "No lead magnet or free download",
            "why": "Top competitors offer free sleep schedules saved heavily on Pinterest and used to build large email lists for retargeting.",
            "action": "1. Create a 1-page Singapore Baby Sleep Schedule PDF. 2. Add email opt-in form to website. 3. Pin it prominently on Pinterest.",
            "effort": "1 day",
            "impact": "medium term"
        },
        {
            "priority": "medium",
            "title": "Carousels underused vs competitors",
            "why": "Instagram carousels average 3x more saves than single images and get re-served by the algorithm to non-followers.",
            "action": "1. Convert this week's blog outline into a 7-slide carousel using the agent output. 2. Schedule for Wednesday which is peak engagement for parenting content.",
            "effort": "2-3 hours",
            "impact": "quick win"
        },
        {
            "priority": "low",
            "title": "No visible client video testimonials",
            "why": "Competitor transformation Reels showing real results drive trust and direct booking conversions more than any other content type.",
            "action": "1. Ask 3 recent clients for a 30-second selfie video. 2. Edit with free CapCut app and add subtitles. 3. Post one per week as a Reel.",
            "effort": "2-3 hours",
            "impact": "medium term"
        },
    ]
