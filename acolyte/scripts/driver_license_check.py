from __future__ import annotations
from typing import Any, Dict, List
from playwright.async_api import async_playwright, Page

URL = "https://moj.gov.pl/uslugi/engine/ng/index?xFormsAppName=UprawnieniaKierowcow&xFormsOrigin=EXTERNAL"

async def run(args: Dict[str, Any]) -> List[Dict[str, Any]]:
    output: List[Dict[str, Any]] = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page: Page = await context.new_page()

        # This is a regular (non-await) setter in the async API too.
        page.set_default_timeout(10_000)

        await page.goto(URL, wait_until="domcontentloaded")

        input_data = (args or {}).get("input") or []

        for item in input_data:
            imie = (item or {}).get("imie") or ""
            nazwisko = (item or {}).get("nazwisko") or ""
            numer = (item or {}).get("numer_dokumentu") or ""

            print(f"Processing for: {imie} {nazwisko} {numer}")

            # Fill the form
            await page.fill("#imiePierwsze", imie)
            await page.fill("#nazwisko", nazwisko)
            await page.fill("#seriaNumerBlankietuDruku", numer)

            # Check submit button availability
            submit_button = await page.query_selector(".btn-primary")
            if not submit_button:
                print(f"Skipping {imie} {nazwisko} due to invalid data (submit button not present).")
                output.append({"imie": imie, "nazwisko": nazwisko, "dokument": numer, "stan": "Niepoprawne dane"})
                continue

            disabled_attr = await submit_button.get_attribute("disabled")
            if disabled_attr is not None:
                print(f"Skipping {imie} {nazwisko} due to invalid data (submit button disabled).")
                output.append({"imie": imie, "nazwisko": nazwisko, "dokument": numer, "stan": "Niepoprawne dane"})
                continue

            await submit_button.click()

            # Prefer Locators for clarity in async code:
            # 1) Check the info banner first
            info_strong = page.locator("upki-search-result-info strong")
            try:
                await info_strong.wait_for(timeout=10_000)
                document_found = (await info_strong.text_content()) or ""
            except Exception:
                document_found = ""

            if document_found.strip() == "Nie znaleziono dokumentu":
                output.append({
                    "imie": imie, "nazwisko": nazwisko, "dokument": numer, "stan": "Nie znaleziono dokumentu"
                })
            else:
                # 2) Otherwise read the state from results area
                state_strong = page.locator("upki-search-results .stan strong")
                try:
                    await state_strong.wait_for(timeout=10_000)
                    state = (await state_strong.text_content()) or ""
                except Exception:
                    # If the element never appears, treat as not found or error
                    state = "Brak wyniku"

                output.append({
                    "imie": imie, "nazwisko": nazwisko, "dokument": numer, "stan": state.strip()
                })

        await context.close()
        await browser.close()

    return output
