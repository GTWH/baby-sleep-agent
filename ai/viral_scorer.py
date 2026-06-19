"""
ai/viral_scorer.py
Scores and ranks posts by viral potential using platform-weighted signals.

Fixed: blog posts from Serper.dev have no view/like counts — they now
get a base relevance score from their position in search results (rank 1
= most relevant = highest score) plus a comments bonus if available.
"""

from typing import List, Dict

WEIGHTS = {
    "instagram": {"views": 0.3,  "likes": 0.3, "comments": 0.2, "saves": 0.2},
    "tiktok":    {"views": 0.5,  "likes": 0.2, "comments": 0.1, "saves": 0.2},
    "pinterest": {"saves": 0.6,  "views": 0.4},
    "blog":      {"relevance": 0.7, "comments": 0.3},   # relevance = search rank proxy
    "youtube":   {"views": 0.4,  "likes": 0.3, "comments": 0.3},
    "reddit":    {"likes": 0.5,  "comments": 0.5},
}

PLATFORM_MULTIPLIER = {
    "tiktok":    1.0,
    "instagram": 0.8,
    "pinterest": 2.0,
    "blog":      1.5,
    "youtube":   1.2,
    "reddit":    0.6,
}

# Blog posts collected via Serper get scored by their search result position
# Position 1 = most relevant = score 10000, position 10 = score 1000
BLOG_POSITION_SCORES = {i: max(10000 - (i-1)*1000, 1000) for i in range(1, 21)}


def rank_posts(posts: List[Dict], top_n: int = 10) -> List[Dict]:
    """Score all posts, add engagement summary, sort and return top N."""

    # Add position index to blog posts for relevance scoring
    blog_count = 0
    for post in posts:
        if post.get("source") == "blog":
            blog_count += 1
            post["_blog_position"] = blog_count

    for post in posts:
        post["viral_score"]        = _score(post)
        post["engagement_summary"] = _fmt(post)

    ranked = sorted(posts, key=lambda p: p["viral_score"], reverse=True)
    for i, p in enumerate(ranked[:top_n], 1):
        p["rank"] = i
        # Clean up internal field
        p.pop("_blog_position", None)

    return ranked[:top_n]


def _score(post: Dict) -> float:
    src = post.get("source", "instagram")
    m   = PLATFORM_MULTIPLIER.get(src, 1.0)
    w   = WEIGHTS.get(src, WEIGHTS["instagram"])

    if src == "blog":
        # Blog posts: relevance score from search position + comments
        position  = post.get("_blog_position", 10)
        relevance = BLOG_POSITION_SCORES.get(position, 1000)
        comments  = post.get("comments", 0)
        raw = relevance * w.get("relevance", 0.7) + comments * w.get("comments", 0.3)
    else:
        raw = sum(post.get(k, 0) * v for k, v in w.items())

    return round(raw * m, 2)


def _fmt(p: Dict) -> str:
    parts = []
    if p.get("views"):    parts.append(f"{_h(p['views'])} views")
    if p.get("likes"):    parts.append(f"{_h(p['likes'])} likes")
    if p.get("saves"):    parts.append(f"{_h(p['saves'])} saves")
    if p.get("comments"): parts.append(f"{_h(p['comments'])} comments")
    if not parts and p.get("source") == "blog":
        return "Top search result"
    return " · ".join(parts) or "—"


def _h(n: int) -> str:
    if n >= 1_000_000: return f"{n/1_000_000:.1f}M"
    if n >= 1_000:     return f"{n/1_000:.0f}K"
    return str(n)
