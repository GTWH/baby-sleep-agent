"""
ai/content_gen.py
Generates all content using Google Gemini 2.0 Flash (free tier).

Retry strategy on 429/503/500/502/504:
  Attempt 1 fails → wait 60s  → retry
  Attempt 2 fails → wait 120s → retry
  Attempt 3 fails → wait 180s → retry
  Attempt 4 fails → wait 240s → retry
  Attempt 5 fails → graceful fallback + logs to FALLBACK_LOG

All fallbacks are recorded in FALLBACK_LOG and saved to the dashboard
report so you can track reliability trends over time.
"""

import asyncio
import urllib.request
import urllib.error
import json
import time
from datetime import datetime
from typing import Dict, List


GEMINI_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models/"
    "gemini-2.5-flash-lite:generateContent"
)

SYSTEM_CONTEXT = """You are the lead content strategist for My Beloved Sleep
(mybelovedsleep.com), a certified baby sleep consulting practice based in
Singapore serving families across Southeast Asia.

Brand voice: warm, expert, deeply empathetic, science-backed, never preachy.
Parents reading our content are exhausted and need reassurance first,
practical steps second. Always end with a clear, gentle call to action.

Market: Singapore parents, pragmatic, value credentials and evidence,
many are first-time parents aged 28-40."""

# Escalating retry waits in seconds
RETRY_WAITS = [30, 60, 90, 120]

# Module-level fallback log — collects events across all calls this run
FALLBACK_LOG: List[Dict] = []


def _call_gemini_with_retry(prompt: str, api_key: str,
                             max_tokens: int = 1000,
                             label: str = "Gemini") -> tuple:
    """
    Call Gemini with escalating retry delays.
    Returns (response_text, status_dict) where status_dict records
    success/failure details for fallback tracking.
    """
    url = f"{GEMINI_URL}?key={api_key}"
    payload = json.dumps({
        "contents": [{"parts": [{"text": f"{SYSTEM_CONTEXT}\n\n{prompt}"}]}],
        "generationConfig": {
            "maxOutputTokens": max_tokens,
            "temperature":     0.7,
        },
    }).encode("utf-8")

    attempts_made = []

    for attempt, wait in enumerate(RETRY_WAITS, start=1):
        try:
            req = urllib.request.Request(
                url, data=payload,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=45) as resp:
                result = json.loads(resp.read())
            text = result["candidates"][0]["content"]["parts"][0]["text"]
            print(f"    ✓ {label} succeeded on attempt {attempt}")
            status = {
                "label":      label,
                "result":     "success",
                "attempts":   attempt,
                "errors":     attempts_made,
                "timestamp":  datetime.utcnow().isoformat(),
            }
            return text, status

        except urllib.error.HTTPError as e:
            if e.code in (429, 500, 502, 503, 504):
                attempts_made.append({"attempt": attempt, "error_code": e.code})
                print(f"    ⏳ {label} HTTP {e.code} — attempt {attempt}/{len(RETRY_WAITS)}, waiting {wait}s...")
                time.sleep(wait)
                continue
            else:
                raise

        except (TimeoutError, OSError) as e:
            attempts_made.append({"attempt": attempt, "error_code": "timeout"})
            print(f"    ⏳ {label} timeout — attempt {attempt}/{len(RETRY_WAITS)}, waiting {wait}s...")
            time.sleep(wait)
            continue

        except Exception as e:
            print(f"    ⚠ {label} unexpected error: {e}")
            raise

    # ── All retries exhausted — graceful fallback ───────────────────────
    fallback_msg = (
        f"[{label} unavailable — Gemini returned errors on all "
        f"{len(RETRY_WAITS)} attempts. Errors: "
        f"{[a['error_code'] for a in attempts_made]}. "
        f"Re-run the agent to regenerate this section.]"
    )
    status = {
        "label":      label,
        "result":     "fallback",
        "attempts":   len(RETRY_WAITS),
        "errors":     attempts_made,
        "timestamp":  datetime.utcnow().isoformat(),
    }
    FALLBACK_LOG.append(status)
    print(f"    ⚠ {label} — all retries exhausted. Fallback recorded.")
    return fallback_msg, status


async def generate_weekly_content(
    viral_posts: List[Dict],
    brand: Dict,
    gemini_api_key: str,
) -> Dict:

    # Clear fallback log for this run
    FALLBACK_LOG.clear()

    top   = viral_posts[0]
    title = top.get("title", "baby sleep tips")[:100]
    src   = top.get("source", "social media")
    eng   = top.get("engagement_summary", "")

    call_statuses = []

    # ── Call 1 of 3: Blog post template ────────────────────────────────
    print("\n    [Gemini 1/3] Blog template...")
    blog, s1 = await asyncio.to_thread(
        _call_gemini_with_retry,
        f"""The top viral post this week was on {src}: "{title}" ({eng}).

Write a blog post template for mybelovedsleep.com:
1. SEO title (keyword-rich, include Singapore if natural)
2. Meta description (155 chars max)
3. Intro hook — 2 warm empathetic paragraphs
4. 5 H2 section headings with 1-sentence descriptions each
5. CTA for a free 15-min discovery call at mybelovedsleep.com
""",
        gemini_api_key, 800, "Blog template"
    )
    call_statuses.append(s1)

    print("    Pausing 60s before next Gemini call...")
    await asyncio.sleep(20)

    # ── Call 2 of 3: Instagram carousel ────────────────────────────────
    print("\n    [Gemini 2/3] Instagram carousel...")
    carousel, s2 = await asyncio.to_thread(
        _call_gemini_with_retry,
        f"""Topic: "{title}"

Create a 5-slide Instagram carousel for @mybelovedsleep.
For each slide: headline (max 8 words) + 2-line body + visual direction.
Then write a 150-word caption with hook, value, save CTA, and 12 hashtags
including #singaporemom and #babysleep.
""",
        gemini_api_key, 600, "IG carousel"
    )
    call_statuses.append(s2)

    print("    Pausing 60s before next Gemini call...")
    await asyncio.sleep(20)

    # ── Call 3 of 3: Reel script ────────────────────────────────────────
    print("\n    [Gemini 3/3] Reel script...")
    reel, s3 = await asyncio.to_thread(
        _call_gemini_with_retry,
        f"""Write a 60-second Reel script for @mybelovedsleep on: "{title}"

Timestamps: 0-3s hook, 4-15s problem, 16-35s insight, 36-50s solution, 51-60s CTA.
Include spoken words, [visual directions in brackets], and "on-screen text in quotes".
""",
        gemini_api_key, 500, "Reel script"
    )
    call_statuses.append(s3)

    fallbacks = [s for s in call_statuses if s["result"] == "fallback"]
    print(f"\n    Content generation complete — {len(fallbacks)}/{len(call_statuses)} calls fell back to placeholder.")

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
            "blog_og":        {"size": "1200x628px",  "style": "Navy background, cream headline, MBS logo, moon icon"},
            "instagram_feed": {"size": "1080x1080px", "style": "Slide 1 of carousel, large headline, brand colours"},
            "pinterest":      {"size": "1000x1500px", "style": "Tall format, headline top, URL watermark bottom"},
        },
        # ── Reliability tracking ────────────────────────────────────────
        "reliability": {
            "calls_total":    len(call_statuses),
            "calls_success":  len([s for s in call_statuses if s["result"] == "success"]),
            "calls_fallback": len(fallbacks),
            "fallback_rate":  f"{round(len(fallbacks)/len(call_statuses)*100)}%",
            "details":        call_statuses,
        },
    }
