import asyncio
import os
from playwright.async_api import async_playwright

URL = "https://icp.administracionelectronica.gob.es/icpplus/index.html"

async def run():

    async with async_playwright() as p:

        browser = await p.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--disable-gpu"
            ]
        )

        context = await browser.new_context()
        page = await context.new_page()

        try:
            await page.goto(URL, timeout=60000)
            await page.wait_for_load_state("domcontentloaded")

            print("Page loaded successfully")

            # test simple
            title = await page.title()
            print("TITLE:", title)

        except Exception as e:
            print("ERROR:", e)

        await browser.close()


if __name__ == "__main__":
    asyncio.run(run())
