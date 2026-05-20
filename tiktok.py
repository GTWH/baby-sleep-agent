"""
ai/viral_scorer.py
Scores and ranks posts by viral potential using
platform-weighted engagement signals.
"""

from typing import List, Dict

WEIGHTS = {
    "instagram": {"views": 0.3,  "likes": 0.3, "comments": 0.2, "saves": 0.2},
    "tiktok":    {"views": 0.5,  "likes": 0.2, "comments": 0.1, "saves": 0.2},
    "pinterest": {"saves": 0.6,  "views": 0.4},
    "blog":      {"views": 0.7,  "likes": 0.1, "comments": 0.2},
}

PLATFORM_MULTIPLIER = {
    "tiktok":    1.0,
    "instagram": 0.8,
    "pinterest": 2.0,
    "blog":      1.5,
}


def rank_posts(posts: List[Dict], top_n: int = 10) -> List[Dict]:
    for post in posts:
        post["viral_score"] = _score(post)
        post["engagement_summary"] = _fmt(post)

    ranked = sorted(posts, key=lambda p: p["viral_score"], reverse=True)
    for i, p in enumerate(ranked[:top_n], 1):
        p["rank"] = i
    return ranked[:top_n]


def _score(post: Dict) -> float:
    src = post.get("source", "instagram")
    w   = WEIGHTS.get(src, WEIGHTS["instagram"])
    m   = PLATFORM_MULTIPLIER.get(src, 1.0)
    raw = sum(post.get(k, 0) * v for k, v in w.items())
    return round(raw * m, 2)


def _fmt(p: Dict) -> str:
    parts = []
    if p.get("views"):    parts.append(f"{_h(p['views'])} views")
    if p.get("likes"):    parts.append(f"{_h(p['likes'])} likes")
    if p.get("saves"):    parts.append(f"{_h(p['saves'])} saves")
    if p.get("comments"): parts.append(f"{_h(p['comments'])} comments")
    return " · ".join(parts) or "—"


def _h(n: int) -> str:
    if n >= 1_000_000: return f"{n/1_000_000:.1f}M"
    if n >= 1_000:     return f"{n/1_000:.0f}K"
    return str(n)
