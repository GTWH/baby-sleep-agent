"""
scrapers/blogs.py
Scrapes top blog articles using Playwright to search Google directly.
NO API KEY REQUIRED — replaces the Google Custom Search API approach.

Uses the same Playwright browser already installed for Instagram/TikTok.
"""

import asyncio
import re
from playwright.async_api import async_playwright


async def scrape_blogs(keywords: list, api_key: str = "", cse_id: str = "") -> list:
    """
    api_key and cse_id params kept for compatibility but no longer used.
    Playwright scrapes Google search results directly.
    """
    posts = []

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-setuid-sandbox",
                  "--disable-dev-shm-usage"]
        )
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                       "AppleWebKit/537.36 (KHTML, like Gecko) "
                       "Chrome/124.0 Safari/537.36",
            locale="en-US",
        )
        page = await context.new_page()

        for kw in keywords[:4]:
            try:
                # Search Google for blog posts from the past week
                query = f"{kw} blog".replace(" ", "+")
                url = f"https://www.google.com/search?q={query}&tbs=qdr:w&num=10"

                await page.goto(url, wait_until="networkidle", timeout=25000)
                await page.wait_for_timeout(2000)

                # Extract search result titles and URLs
                results = await page.eval_on_selector_all(
                    "h3",
                    "els => els.map(e => ({"
                    "  title: e.innerText.trim(),"
                    "  url: e.closest('a') ? e.closest('a').href : ''"
                    "})).filter(r => r.title.length > 10 && r.url.startsWith('http'))"
                )

                # Extract snippets (description text under each result)
                snippets = await page.eval_on_selector_all(
                    "[data-sncf], .VwiC3b, .yXK7lf",
                    "els => els.map(e => e.innerText.trim()).filter(t => t.length > 30)"
                )

                for i, result in enumerate(results[:8]):
                    # Skip Google's own pages
                    if "google.com" in result.get("url", ""):
                        continue
                    posts.append({
                        "source":       "blog",
                        "id":           result.get("url", ""),
                        "title":        result.get("title", "")[:150],
                        "url":          result.get("url", ""),
                        "author":       _extract_domain(result.get("url", "")),
                        "description":  snippets[i] if i < len(snippets) else "",
                        "views":        0,
                        "likes":        0,
                        "saves":        0,
                        "published_at": "",
                    })

                await asyncio.sleep(3)  # polite delay between searches

            except Exception as e:
                print(f"    ⚠ Blog search '{kw}': {e}")
                continue

        await browser.close()

    print(f"    Blogs → {len(posts)} articles via Playwright/Google")
    return posts


def _extract_domain(url: str) -> str:
    """Extract domain name from URL for display."""
    try:
        match = re.search(r"https?://(?:www\.)?([^/]+)", url)
        return match.group(1) if match else url
    except Exception:
        return url
