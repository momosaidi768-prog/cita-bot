import asyncio
import aiohttp
from playwright.async_api import async_playwright

TOKEN = "8202293986:AAFDFxfm9O_ZfWWL9p4UAXmeTV7M4fSWtps"
ADMIN_ID = 6675176280
TG_URL = f"https://api.telegram.org/bot{TOKEN}"

running = False

# ================= TELEGRAM =================

class Telegram:
    def __init__(self):
        self.session = None

    async def init(self):
        if not self.session:
            self.session = aiohttp.ClientSession()

    async def send(self, msg):
        await self.init()
        try:
            async with self.session.post(
                f"{TG_URL}/sendMessage",
                data={"chat_id": ADMIN_ID, "text": msg}
            ) as r:
                print("TG:", await r.text())
        except Exception as e:
            print("TG ERROR:", e)

tg = Telegram()

# ================= WORKER =================

async def worker():
    global running

    print("🚀 WORKER STARTED")

    try:
        async with async_playwright() as p:

            browser = await p.chromium.launch(
                channel="chromium",
                headless=True,
                args=[
                    "--no-sandbox",
                    "--disable-dev-shm-usage",
                    "--disable-gpu"
                ]
            )

            page = await browser.new_page()

            await page.goto("https://example.com")

            await tg.send("🤖 Bot started successfully")

            while running:
                print("🔁 ALIVE WORKING...")
                await asyncio.sleep(5)

    except Exception as e:
        print("❌ WORKER ERROR:", e)
        await tg.send(f"❌ Worker crashed: {e}")

# ================= COMMANDS =================

async def handle(text):
    global running

    print("CMD:", text)

    if text == "/startbot":

        if running:
            return

        running = True
        asyncio.create_task(worker())

        await tg.send("🚀 Bot started")

    elif text == "/stopbot":

        running = False
        await tg.send("⛔ Bot stopped")

# ================= TELEGRAM POLLING =================

async def main():

    print("🔥 BOT STARTING...")

    offset = None

    await tg.send("🤖 BOT ONLINE")

    while True:

        try:
            async with aiohttp.ClientSession() as s:
                async with s.get(
                    f"{TG_URL}/getUpdates?offset={offset}"
                ) as r:

                    data = await r.json()

            if data.get("ok"):

                for upd in data.get("result", []):

                    offset = upd["update_id"] + 1

                    if "message" in upd:

                        chat_id = upd["message"]["chat"]["id"]
                        text = upd["message"].get("text", "")

                        if chat_id == ADMIN_ID:
                            await handle(text)

        except Exception as e:
            print("MAIN ERROR:", e)

        await asyncio.sleep(2)

# ================= START =================

if __name__ == "__main__":
    asyncio.run(main())
