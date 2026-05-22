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
            async with self.session.post(
                f"{TG_URL}/sendMessage",
                data={"chat_id": ADMIN_ID, "text": msg}
            ) as r:
                await r.text()
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

        print(f"📍 Checking {city}")

        selects = page.locator("select")
        count = await selects.count()

        if count < 2:
            return None

        # city select
        try:
            await selects.nth(0).select_option(label=city)
        except:
            return None

        await page.click("input[type='submit']")
        await page.wait_for_load_state("domcontentloaded")

        # service select
        try:
            await selects.nth(0).select_option(label=SERVICE)
        except:
            return None

        await page.click("input[type='submit']")
        await page.wait_for_load_state("domcontentloaded")

        html = await page.content()

        if "no hay citas" in html.lower():
            return None

        print("🔥 FOUND")
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
                            try:
                                await page.screenshot(path="shot.png")

                                await tg.send(
                                    f"🔥 FOUND\n{name}\n{nie}\n{city}\n{result}"
                                )
                            except:
                                pass

                            await asyncio.sleep(30)

                        await asyncio.sleep(2)

                await asyncio.sleep(5)

            await browser.close()

    except Exception as e:
        await tg.send(f"❌ Worker crashed: {str(e)[:500]}")


# ================= COMMANDS =================

async def handle(text):
    global running

    if text == "/startbot":
        if running:
            await tg.send("⚠️ Already running")
            return

        running = True
        asyncio.create_task(worker())
        await tg.send("🚀 Started")

    elif text == "/stopbot":
        running = False
        await tg.send("⛔ Stopped")


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


if __name__ == "__main__":
    asyncio.run(main())
