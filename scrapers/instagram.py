"""
scrapers/instagram.py
Scrapes public Instagram hashtag pages using Playwright.
No API key required — reads publicly visible posts only.
"""

import asyncio
import re
from playwright.async_api import async_playwright


async def scrape_instagram(hashtags: list) -> list:
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

        for tag in hashtags[:5]:           # cap at 5 tags to stay fast
            try:
                url = f"https://www.instagram.com/explore/tags/{tag}/"
                await page.goto(url, wait_until="networkidle", timeout=25000)
                await page.wait_for_timeout(3000)

                # Pull shared data JSON Instagram embeds in the page
                content = await page.content()
                pattern = r'"node":\{"__typename":"GraphImage".*?"shortcode":"(\w+)".*?"edge_liked_by":\{"count":(\d+)\}.*?"edge_media_to_comment":\{"count":(\d+)\}'
                matches = re.findall(pattern, content)[:10]

                # Also grab alt texts / captions visible in DOM
                captions = await page.eval_on_selector_all(
                    'article img[alt]',
                    'els => els.map(e => e.getAttribute("alt")).filter(Boolean)'
                )

                for i, caption in enumerate(captions[:10]):
                    likes = int(matches[i][1]) if i < len(matches) else 0
                    comments = int(matches[i][2]) if i < len(matches) else 0
                    shortcode = matches[i][0] if i < len(matches) else ""
                    posts.append({
                        "source":    "instagram",
                        "id":        shortcode,
                        "title":     caption[:150],
                        "url":       f"https://www.instagram.com/p/{shortcode}/",
                        "author":    f"#{tag}",
                        "likes":     likes,
                        "comments":  comments,
                        "views":     likes * 8,     # proxy: views ≈ 8× likes
                        "saves":     likes // 10,   # proxy: saves ≈ 10% likes
                        "hashtags":  [tag],
                        "published_at": "",
                    })

                await asyncio.sleep(2)              # polite delay between tags

            except Exception as e:
                print(f"    ⚠ Instagram #{tag}: {e}")
                continue

        await browser.close()

    print(f"    Instagram → {len(posts)} posts from {len(hashtags[:5])} hashtags")
    return posts
