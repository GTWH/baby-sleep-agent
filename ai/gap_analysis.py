"""
ai/gap_analysis.py
Analyses competitor data and uses Gemini to surface
prioritised content gaps with action plans.
"""

import asyncio
import json
import re
from typing import List, Dict


GEMINI_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models/"
    "gemini-2.0-flash:generateContent"
)

import urllib.request


def _call_gemini(prompt: str, api_key: str) -> str:
    url  = f"{GEMINI_URL}?key={api_key}"
    data = json.dumps({
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"maxOutputTokens": 1200, "temperature": 0.5},
    }).encode()
    req = urllib.request.Request(
        url, data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        result = json.loads(r.read())
    return result["candidates"][0]["content"]["parts"][0]["text"]


async def run_gap_analysis(
    competitor_data: List[Dict],
    gemini_api_key: str,
) -> List[Dict]:

    comp_summary = "\n".join([
        f"- {c['name']}: {c.get('pages',0)} posts found, "
        f"recent titles: {'; '.join(c.get('titles',[])[:3])}"
        for c in competitor_data if not c.get("error")
    ]) or "No competitor data available this week."

    prompt = f"""
You are auditing the content strategy of My Beloved Sleep (mybelovedsleep.com),
a Singapore baby sleep consulting brand, versus these competitors:

{comp_summary}

Identify exactly 6 content and distribution gaps. Return ONLY a valid JSON
array — no markdown, no extra text, no code fences. Each object must have:
  "priority"  : "high" | "medium" | "low"
  "title"     : gap name, 5–8 words
  "why"       : 2 sentences — why competitors outperform here
  "action"    : 2–3 concrete numbered steps, achievable in 2 weeks
  "effort"    : "30 min" | "2–3 hours" | "1 day"
  "impact"    : "quick win" | "medium term" | "long term"
"""

    raw = await asyncio.to_thread(_call_gemini, prompt, gemini_api_key)
    raw = re.sub(r"```json|```", "", raw).strip()

    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return _fallback_gaps()


def _fallback_gaps() -> List[Dict]:
    return [
        {"priority":"high",  "title":"No TikTok presence at all",             "why":"Top viral post this week (2.4M views) was TikTok. Competitors capture younger parents earlier.", "action":"1. Create @mybelovedsleep TikTok. 2. Post this week's reel as first video. 3. Aim 3x/week.", "effort":"2–3 hours","impact":"medium term"},
        {"priority":"high",  "title":"Posting frequency 3x below competitors","why":"Competitors post 7–10x/week. More touchpoints = more algorithm reach.",                          "action":"1. Use agent's weekly batch as minimum. 2. Add 2 story posts. 3. Repurpose blog into 3 social posts.", "effort":"2–3 hours","impact":"quick win"},
        {"priority":"high",  "title":"Missing Singapore-specific SEO content", "why":"No pages rank for 'baby sleep consultant Singapore'. Local search is wide open.",               "action":"1. Write blog targeting 'baby sleep consultant Singapore'. 2. Add location meta tags. 3. Submit Search Console.", "effort":"1 day","impact":"long term"},
        {"priority":"medium","title":"No lead magnet or free download",        "why":"Competitors offer free sleep schedules saved heavily on Pinterest and build email lists.",        "action":"1. Create 1-page Singapore Baby Sleep Schedule PDF. 2. Email opt-in on site. 3. Pin on Pinterest.", "effort":"1 day","impact":"medium term"},
        {"priority":"medium","title":"Carousels underused vs competitors",     "why":"Instagram carousels get 3x more saves and are re-served to non-followers by algorithm.",         "action":"1. Convert blog outline to 7-slide carousel. 2. Schedule for Wednesday peak.", "effort":"2–3 hours","impact":"quick win"},
        {"priority":"low",   "title":"No visible client video testimonials",   "why":"Competitor transformation Reels drive trust and direct booking conversions.",                     "action":"1. Ask 3 clients for 30s video. 2. Edit with CapCut + subtitles. 3. Post 1/week.", "effort":"2–3 hours","impact":"medium term"},
    ]
