from __future__ import annotations
from typing import Any, Dict
from playwright.async_api import async_playwright

async def run(args: Dict[str, Any]) -> Dict[str, Any]:
    """
    Example: fetch DuckDuckGo, search for a query, return first result text.
    Args:
      args["q"]: search query (default "fastapi")
    """
    query = (args or {}).get("q", "fastapi")

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-dev-shm-usage"],
        )
        context = await browser.new_context()
        page = await context.new_page()

        await page.goto("https://duckduckgo.com/")
        await page.fill("input[name=q]", query)
        await page.keyboard.press("Enter")
        await page.wait_for_selector("#links .result__title", timeout=15000)

        first = await page.locator("#links .result__title").first.inner_text()
        url = await page.locator("#links .result__url").first.inner_text()

        await context.close()
        await browser.close()

    return {"query": query, "first_result_title": first, "first_result_url": url}
