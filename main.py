import asyncio
import sqlite3
import aiohttp
from playwright.async_api import async_playwright

TOKEN = "PUT_YOUR_BOT_TOKEN"
ADMIN_ID = 6675176280
TG_URL = f"https://api.telegram.org/bot{TOKEN}/sendMessage"

async def send(msg):
    async with aiohttp.ClientSession() as s:
        await s.post(TG_URL, data={
            "chat_id": ADMIN_ID,
            "text": msg
        })

async def main():

    print("🔥 BOT STARTING...")
    await send("🤖 BOT STARTED")

    async with async_playwright() as p:

        print("🚀 Launching browser...")

        browser = await p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-dev-shm-usage"]
        )

        page = await browser.new_page()

        await page.goto("https://example.com")

        print("✅ PAGE LOADED")
        await send("✅ System running")

        while True:
            await asyncio.sleep(10)
            print("RUNNING...")

if __name__ == "__main__":
    asyncio.run(main())
