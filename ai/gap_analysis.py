"""
ai/gap_analysis.py
Analyses competitor data and uses Gemini to surface
prioritised content gaps. Tracks fallbacks for reliability reporting.
"""

import asyncio
import json
import re
import time
import urllib.request
import urllib.error
from datetime import datetime
from typing import List, Dict

GEMINI_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models/"
    "gemini-2.0-flash:generateContent"
)

RETRY_WAITS = [60, 120, 180, 240]


def _call_gemini_with_retry(prompt: str, api_key: str) -> tuple:
    """Returns (text, status_dict) — same pattern as content_gen.py."""
    url = f"{GEMINI_URL}?key={api_key}"
    payload = json.dumps({
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"maxOutputTokens": 1000, "temperature": 0.5},
    }).encode()

    attempts_made = []

    for attempt, wait in enumerate(RETRY_WAITS, start=1):
        try:
            req = urllib.request.Request(
                url, data=payload,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=30) as r:
                result = json.loads(r.read())
            print(f"    ✓ Gap analysis succeeded on attempt {attempt}")
            status = {
                "label":     "Gap analysis",
                "result":    "success",
                "attempts":  attempt,
                "errors":    attempts_made,
                "timestamp": datetime.utcnow().isoformat(),
            }
            return result["candidates"][0]["content"]["parts"][0]["text"], status

        except urllib.error.HTTPError as e:
            if e.code in (429, 500, 502, 503, 504):
                attempts_made.append({"attempt": attempt, "error_code": e.code})
                print(f"    ⏳ Gap analysis HTTP {e.code} — attempt {attempt}/{len(RETRY_WAITS)}, waiting {wait}s...")
                time.sleep(wait)
                continue
            else:
                raise

    # All retries exhausted
    status = {
        "label":     "Gap analysis",
        "result":    "fallback",
        "attempts":  len(RETRY_WAITS),
        "errors":    attempts_made,
        "timestamp": datetime.utcnow().isoformat(),
    }
    print(f"    ⚠ Gap analysis — all retries exhausted. Using built-in fallback gaps.")
    return "[]", status


async def run_gap_analysis(
    competitor_data: List[Dict],
    gemini_api_key: str,
) -> tuple:
    """Returns (gaps_list, status_dict)."""

    comp_summary = "\n".join([
        f"- {c['name']}: {c.get('pages', 0)} posts, "
        f"titles: {'; '.join(c.get('titles', [])[:3])}"
        for c in competitor_data if not c.get("error")
    ]) or "No competitor data available."

    prompt = f"""
You are auditing My Beloved Sleep (mybelovedsleep.com) vs these competitors:
{comp_summary}

Return ONLY a valid JSON array of exactly 6 gap objects. No markdown. Each object:
  "priority"  : "high" | "medium" | "low"
  "title"     : 5-8 word gap name
  "why"       : 2 sentences why competitors outperform here
  "action"    : 2-3 numbered concrete steps achievable in 2 weeks
  "effort"    : "30 min" | "2-3 hours" | "1 day"
  "impact"    : "quick win" | "medium term" | "long term"
"""

    print("\n    [Gemini 4/4] Gap analysis — pausing 60s first...")
    await asyncio.sleep(60)

    raw, status = await asyncio.to_thread(_call_gemini_with_retry, prompt, gemini_api_key)
    raw = re.sub(r"```json|```", "", raw).strip()

    try:
        gaps = json.loads(raw)
        if status["result"] == "success":
            print(f"    ✓ {len(gaps)} gaps identified")
        return gaps, status
    except json.JSONDecodeError:
        status["result"] = "fallback"
        status["parse_error"] = True
        return _fallback_gaps(), status


def _fallback_gaps() -> List[Dict]:
    return [
        {"priority":"high",   "title":"No TikTok presence at all",              "why":"Top viral posts this week were on TikTok. Competitors capture younger parents earlier in their journey.","action":"1. Create @mybelovedsleep TikTok. 2. Post this week's reel as first video. 3. Aim 3x/week.","effort":"2-3 hours","impact":"medium term"},
        {"priority":"high",   "title":"Posting frequency 3x below competitors", "why":"Competitors post 7-10x/week. More touchpoints means more algorithm exposure.","action":"1. Use agent weekly batch as minimum. 2. Add 2 story posts/week. 3. Repurpose each blog into 3 posts.","effort":"2-3 hours","impact":"quick win"},
        {"priority":"high",   "title":"Missing Singapore-specific SEO content",  "why":"No pages rank for 'baby sleep consultant Singapore'. Local search is wide open.","action":"1. Write blog targeting 'baby sleep consultant Singapore'. 2. Add location meta tags. 3. Submit to Search Console.","effort":"1 day","impact":"long term"},
        {"priority":"medium", "title":"No lead magnet or free download",         "why":"Competitors offer free sleep schedules saved heavily on Pinterest and building email lists.","action":"1. Create 1-page Singapore Baby Sleep Schedule PDF. 2. Add email opt-in. 3. Pin on Pinterest.","effort":"1 day","impact":"medium term"},
        {"priority":"medium", "title":"Carousels underused vs competitors",      "why":"Instagram carousels get 3x more saves and get re-served to non-followers by the algorithm.","action":"1. Convert blog outline to 7-slide carousel. 2. Schedule for Wednesday peak engagement.","effort":"2-3 hours","impact":"quick win"},
        {"priority":"low",    "title":"No visible client video testimonials",    "why":"Competitor transformation Reels drive trust and direct booking conversions.","action":"1. Ask 3 clients for 30s video. 2. Edit with CapCut and subtitles. 3. Post 1/week.","effort":"2-3 hours","impact":"medium term"},
    ]
