"""
ai/content_gen.py
Generates all content using Google Gemini 1.5 Flash.

FREE tier limits (more than enough for weekly runs):
  - 15 requests/minute
  - 1,500 requests/day
  - 1 million tokens/minute

Setup (3 minutes, free):
  1. Go to aistudio.google.com
  2. Click "Get API key" → Create API key → copy it
  3. Add to GitHub Secrets as: GEMINI_API_KEY
"""

import asyncio
import urllib.request
import urllib.parse
import json
from typing import Dict, List


GEMINI_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models/"
    "gemini-3.5-flash:generateContent"
)

SYSTEM_CONTEXT = """You are the lead content strategist for My Beloved Sleep
(mybelovedsleep.com), a certified baby sleep consulting practice based in
Singapore serving families across Southeast Asia.

Brand voice: warm, expert, deeply empathetic, science-backed, never preachy.
Parents reading our content are exhausted and need reassurance first,
practical steps second. Always end with a clear, gentle call to action.

Market: Singapore parents, pragmatic, value credentials and evidence,
many are first-time parents aged 28–40."""


def _call_gemini(prompt: str, api_key: str, max_tokens: int = 1500) -> str:
    """Synchronous Gemini API call."""
    url = f"{GEMINI_URL}?key={api_key}"
    payload = {
        "contents": [{
            "parts": [{"text": f"{SYSTEM_CONTEXT}\n\n{prompt}"}]
        }],
        "generationConfig": {
            "maxOutputTokens": max_tokens,
            "temperature":     0.7,
        }
    }
    data = json.dumps(payload).encode("utf-8")
    req  = urllib.request.Request(
        url, data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        result = json.loads(resp.read())
    return result["candidates"][0]["content"]["parts"][0]["text"]


async def generate_weekly_content(
    viral_posts: List[Dict],
    brand: Dict,
    gemini_api_key: str,
) -> Dict:

    top   = viral_posts[0]
    title = top.get("title", "baby sleep tips")[:100]
    src   = top.get("source", "social media")
    eng   = top.get("engagement_summary", "")

    # ── Blog post template ──────────────────────────────────────────────
    blog = await asyncio.to_thread(_call_gemini, f"""
The top viral post this week was on {src}: "{title}" ({eng}).

Write a complete blog post template for mybelovedsleep.com adapted from this topic:
1. SEO title (compelling, keyword-rich, include "Singapore" if natural)
2. Meta description (155 characters max)
3. Intro hook — 2 warm paragraphs: empathetic opening, then reassurance
4. H2 section outline — 5 sections with 2-sentence descriptions
5. "Real family story" placeholder section
6. CTA block for a free 15-min discovery call at mybelovedsleep.com
7. 3 Pinterest image description ideas for the post

Use clear section labels.
""", gemini_api_key, max_tokens=1200)

    # ── Instagram carousel ──────────────────────────────────────────────
    carousel = await asyncio.to_thread(_call_gemini, f"""
Based on this week's top viral topic: "{title}"

Create a 5-slide Instagram carousel for @mybelovedsleep:
For each slide:
  - Headline: max 8 words, punchy, stops the scroll
  - Body: 2 lines max, conversational, fits a phone screen
  - Visual direction: what to show

Then write a caption (150–180 words):
  - Hook opener (first line must stop scrolling)
  - Value body
  - Save CTA
  - 15 hashtags (mix of niche and broad, include #singaporemom)
""", gemini_api_key, max_tokens=700)

    # ── 60-second Reel script ───────────────────────────────────────────
    reel = await asyncio.to_thread(_call_gemini, f"""
Write a 60-second Instagram/TikTok Reel script for @mybelovedsleep on:
"{title}"

Format with timestamps:
  0–3s   : hook (stop-scroll, spoken to camera)
  4–15s  : problem (what parents are experiencing)
  16–35s : insight (the science or key truth)
  36–50s : solution steps (numbered, fast)
  51–60s : soft CTA (free discovery call, link in bio)

Include:
  - Spoken words exactly as said
  - [Visual direction in brackets]
  - "On-screen text in quotes"
""", gemini_api_key, max_tokens=500)

    return {
        "top_post_meta": {
            "title":       title,
            "source":      src,
            "engagement":  eng,
            "viral_score": top.get("viral_score", 0),
            "url":         top.get("url", ""),
        },
        "blog":               blog,
        "instagram_carousel": carousel,
        "reel_script":        reel,
        "thumbnail_spec": {
            "blog_og":        {"size": "1200×628px",  "style": "Navy background, cream headline, MBS logo, moon icon"},
            "instagram_feed": {"size": "1080×1080px", "style": "Slide 1 of carousel, large headline, brand colours"},
            "pinterest":      {"size": "1000×1500px", "style": "Tall format, headline top, URL watermark bottom"},
        },
    }
