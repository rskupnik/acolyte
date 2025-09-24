from __future__ import annotations
from typing import Any, Dict, Optional, List, Tuple
from playwright.async_api import async_playwright, Page

# Preferred selectors for the HTML-lite page (stable)
HTML_SELECTORS: List[str] = [
    "a.result__a",                # classic
    "#links .result__title a",    # older fallback
]

# Fallback selectors for the main SPA page if /html/ fails
SPA_SELECTORS: List[str] = [
    'a[data-testid="result-title-a"]',
    '[data-testid="result"] a[href]',
    'article a[href]',
]

async def _first_result(page: Page, selectors: List[str]) -> Optional[Tuple[str, str]]:
    """Try a list of selectors and return (title, href) of the first match."""
    for sel in selectors:
        loc = page.locator(sel).first
        if await loc.count() > 0:
            # Wait for it to be attached/visible enough
            try:
                await loc.wait_for(timeout=5000)
                title = (await loc.inner_text()).strip()
                href = await loc.get_attribute("href")
                if href:
                    return title, href
            except Exception:
                continue
    return None

async def run(args: Dict[str, Any]) -> Dict[str, Any]:
    """
    Example: search DuckDuckGo and return the first organic result.
    Args:
      args["q"]: search query (default "fastapi")
      args["region"]: optional region code (e.g., "us-en") for /html/ endpoint
    """
    query = (args or {}).get("q", "fastapi")
    region = (args or {}).get("region")  # e.g., "us-en"

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-dev-shm-usage"],
        )
        context = await browser.new_context(
            user_agent=(
                "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
        )
        page = await context.new_page()

        # 1) Try the HTML-lite endpoint first (stable DOM).
        # Docs/community consistently recommend /html for scraping. :contentReference[oaicite:0]{index=0}
        base = "https://duckduckgo.com/html/"
        url = f"{base}?q={query}"
        if region:
            url += f"&kl={region}"
        await page.goto(url, wait_until="domcontentloaded")
        # On /html, the search box is standard and results load server-side.
        found = await _first_result(page, HTML_SELECTORS)

        # 2) Fallback to the main SPA if needed, trying several robust selectors.
        if not found:
            await page.goto(f"https://duckduckgo.com/?q={query}", wait_until="domcontentloaded")
            # Wait for main results container in a generic way
            try:
                await page.wait_for_selector("main, #links, [data-testid='mainline']", timeout=10000)
            except Exception:
                pass
            found = await _first_result(page, SPA_SELECTORS)

        await context.close()
        await browser.close()

    if not found:
        raise RuntimeError("Could not locate any search results on DuckDuckGo")

    title, href = found
    return {"query": query, "first_result_title": title, "first_result_url": href}
