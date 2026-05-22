import asyncio
import aiohttp
from playwright.async_api import async_playwright

TOKEN = "8202293986:AAFDFxfm9O_ZfWWL9p4UAXmeTV7M4fSWtps"
ADMIN_ID = 6675176280

BASE_URL = f"https://api.telegram.org/bot{TOKEN}"

URL = "https://example.com"  # بدّلها بأي صفحة قانونية

running = False
last_state = None


# ================= TELEGRAM =================

class Telegram:
    def __init__(self):
        self.session = None

    async def init(self):
        if not self.session:
            self.session = aiohttp.ClientSession()

    async def send(self, msg):
        await self.init()

        msg = str(msg)

        if len(msg) > 3500:
            msg = msg[:3500] + "\n...\nTRUNCATED"

        try:
            await self.session.post(
                f"{BASE_URL}/sendMessage",
                data={"chat_id": ADMIN_ID, "text": msg}
            )
        except Exception as e:
            print("TG ERROR:", e)


tg = Telegram()


# ================= PAGE CHECK =================

async def check_page(page):
    await page.goto(URL, wait_until="domcontentloaded")
    html = await page.content()

    if "no hay citas" in html.lower():
        return "EMPTY"

    return hash(html)  # detect change


# ================= WORKER =================

async def worker():

    global running, last_state

    print("🚀 WORKER STARTED")

    async with async_playwright() as p:

        browser = await p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-dev-shm-usage"]
        )

        page = await browser.new_page()

        await tg.send("🤖 Monitoring started")

        while running:

            try:
                state = await check_page(page)

                if last_state is None:
                    last_state = state

                elif state != last_state:
                    await tg.send("🔥 CHANGE DETECTED ON PAGE")
                    last_state = state

                print("🔁 checking...")
                await asyncio.sleep(60)

            except Exception as e:
                print("WORKER ERROR:", e)
                await asyncio.sleep(10)

        await browser.close()


# ================= COMMANDS =================

async def handle(text):
    global running, worker_task

    if text == "/startbot":
        if running:
            await tg.send("⚠️ Already running")
            return

        running = True
        asyncio.create_task(worker())
        await tg.send("🚀 Bot started")

    elif text == "/stopbot":
        running = False
        await tg.send("⛔ Bot stopped")


# ================= TELEGRAM LOOP =================

async def main():

    print("🔥 BOT STARTING...")

    offset = None

    await tg.send("🤖 BOT ONLINE")

    while True:

        try:
            async with aiohttp.ClientSession() as s:
                async with s.get(
                    f"{BASE_URL}/getUpdates?offset={offset}"
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


if __name__ == "__main__":
    asyncio.run(main())
