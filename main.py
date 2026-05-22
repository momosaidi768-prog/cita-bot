import asyncio
import aiohttp
from playwright.async_api import async_playwright

TOKEN = "PUT_YOUR_BOT_TOKEN"
ADMIN_ID = 6675176280
TG_URL = f"https://api.telegram.org/bot{TOKEN}"

running = True


async def send(msg):
    async with aiohttp.ClientSession() as s:
        await s.post(f"{TG_URL}/sendMessage", data={
            "chat_id": ADMIN_ID,
            "text": msg
        })


async def worker():
    try:
        async with async_playwright() as p:
            print("🚀 Browser starting...")

            browser = await p.chromium.launch(
                headless=True,
                args=["--no-sandbox"]
            )

            page = await browser.new_page()

            print("✅ Browser started")

            while running:
                print("🔁 Bot running...")
                await asyncio.sleep(5)

    except Exception as e:
        print("WORKER ERROR:", e)


async def main():
    print("🔥 BOT STARTING...")

    await send("🤖 BOT ONLINE")

    task = asyncio.create_task(worker())

    while True:
        await asyncio.sleep(10)


if __name__ == "__main__":
    asyncio.run(main())
