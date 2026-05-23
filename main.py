import asyncio
import sqlite3
import aiohttp
from playwright.async_api import async_playwright

# ================= CONFIG =================

TOKEN = "8202293986:AAFDFxfm9O_ZfWWL9p4UAXmeTV7M4fSWtps"
ADMIN_ID = 6675176280

TG_URL = f"https://api.telegram.org/bot{TOKEN}"

URL = "https://icp.administracionelectronica.gob.es/icpplus/index.html"
SERVICE = "POLICÍA - TOMA DE HUELLAS (EXPEDICIÓN DE TARJETA)"

running = False
worker_task = None

# ================= TELEGRAM =================

class Telegram:
    def __init__(self):
        self.session = None

    async def init(self):
        if self.session is None:
            self.session = aiohttp.ClientSession()

    async def send(self, msg):
        await self.init()

        msg = str(msg)

        if len(msg) > 3500:
            msg = msg[:3500]

        try:
            await self.session.post(
                f"{TG_URL}/sendMessage",
                data={"chat_id": ADMIN_ID, "text": msg}
            )
        except Exception as e:
            print("TG ERROR:", e)

tg = Telegram()

# ================= DATABASE =================

conn = sqlite3.connect("users.db", check_same_thread=False)
cur = conn.cursor()

cur.execute("""
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT,
    nie TEXT,
    phone TEXT,
    email TEXT,
    cities TEXT,
    active INTEGER DEFAULT 1
)
""")

conn.commit()

def get_users():
    cur.execute("""
        SELECT name, nie, phone, email, cities
        FROM users
        WHERE active=1
    """)
    return cur.fetchall()

# ================= SAFE NAV =================

async def safe_goto(page, url):
    for _ in range(3):
        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=60000)
            return True
        except:
            await asyncio.sleep(2)
    return False

# ================= CHECK =================

async def check(page, city):
    try:
        ok = await safe_goto(page, URL)
        if not ok:
            return None

        selects = page.locator("select")

        if await selects.count() < 2:
            return None

        await selects.nth(0).select_option(label=city)
        await page.click("input[type='submit']")
        await page.wait_for_load_state("domcontentloaded")

        await selects.nth(0).select_option(label=SERVICE)
        await page.click("input[type='submit']")
        await page.wait_for_load_state("domcontentloaded")

        html = await page.content()

        if "no hay citas" in html.lower():
            return None

        return page.url

    except Exception as e:
        print("CHECK ERROR:", e)
        return None

# ================= WORKER =================

async def worker():
    global running

    print("🚀 WORKER STARTED")

    try:
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

            await tg.send("🤖 Bot started")

            while running:

                users = get_users()

                for user in users:

                    name, nie, phone, email, cities = user
                    city_list = [c.strip() for c in cities.split(",")]

                    for city in city_list:

                        result = await check(page, city)

                        if result:
                            await page.screenshot(path="shot.png")

                            await tg.send(
                                f"🔥 FOUND\n{name}\n{nie}\n{city}\n{result}"
                            )

                            await asyncio.sleep(30)

                        await asyncio.sleep(2)

                await asyncio.sleep(5)

            await browser.close()

    except Exception as e:
        await tg.send(f"❌ Worker crashed: {str(e)[:400]}")

# ================= COMMANDS =================

async def handle(text):
    global running, worker_task

    if text == "/startbot":

        if running:
            return  # ❌ يمنع spam

        running = True
        worker_task = asyncio.create_task(worker())

        await tg.send("🚀 Bot started")

    elif text == "/stopbot":

        if not running:
            return

        running = False

        if worker_task:
            worker_task.cancel()

        await tg.send("⛔ Bot stopped")

# ================= MAIN LOOP =================

async def main():

    print("🔥 BOT STARTING...")

    offset = None

    await tg.send("🤖 BOT ONLINE")

    while True:

        try:
            async with aiohttp.ClientSession() as s:
                async with s.get(f"{TG_URL}/getUpdates?offset={offset}") as r:
                    data = await r.json()

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
