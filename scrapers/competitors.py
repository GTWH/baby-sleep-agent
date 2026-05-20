"""
scrapers/competitors.py
Scrapes competitor blog pages using Playwright.
Extracts recent post titles, descriptions, and publishing frequency.
No API key required.
"""

import asyncio
from playwright.async_api import async_playwright


async def scrape_competitors(competitors: list) -> list:
    results = []
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-setuid-sandbox",
                  "--disable-dev-shm-usage"]
        )
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                       "AppleWebKit/537.36 Chrome/124.0 Safari/537.36",
        )
        page = await context.new_page()

        for comp in competitors:
            try:
                await page.goto(comp["url"], wait_until="networkidle", timeout=25000)
                await page.wait_for_timeout(2000)

                # Extract all article/post titles
                titles = await page.eval_on_selector_all(
                    'h1, h2, h3, article h2, .post-title, [class*="title"], [class*="heading"]',
                    'els => [...new Set(els.map(e => e.innerText.trim()).filter(t => t.length > 10 && t.length < 120))]'
                )

                # Extract meta description and visible text snippets
                desc = await page.eval_on_selector(
                    'meta[name="description"]',
                    'el => el ? el.getAttribute("content") : ""'
                ).catch(lambda _: "")

                snippets = await page.eval_on_selector_all(
                    'p',
                    'els => els.map(e => e.innerText.trim()).filter(t => t.length > 40 && t.length < 300).slice(0, 3)'
                )

                results.append({
                    "name":    comp["name"],
                    "url":     comp["url"],
                    "titles":  titles[:8],
                    "desc":    desc,
                    "content": snippets,
                    "pages":   len(titles),
                    "error":   None,
                })
                print(f"    ✓ {comp['name']}: {len(titles)} posts found")

            except Exception as e:
                print(f"    ⚠ {comp['name']}: {e}")
                results.append({
                    "name":   comp["name"],
                    "url":    comp["url"],
                    "titles": [],
                    "desc":   "",
                    "content": [],
                    "pages":  0,
                    "error":  str(e),
                })

            await asyncio.sleep(2)

        await browser.close()

    return results
