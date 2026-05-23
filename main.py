import asyncio
import sqlite3
import aiohttp
import os
from playwright.async_api import async_playwright

# ================= CONFIG =================

TOKEN = os.getenv("8202293986:AAFDFxfm9O_ZfWWL9p4UAXmeTV7M4fSWtps")

ADMIN_ID = 6675176280

PROXY_SERVER = "http://104.207.43.86:3129"
PROXY_USER = "umtm2swfzlr7"
PROXY_PASS = "15ngynzfxzl2nsm"

TG_URL = f"https://api.telegram.org/bot{TOKEN}"

URL = "https://icp.administracionelectronica.gob.es/icpplus/index.html"

SERVICE = "POLICÍA - TOMA DE HUELLAS (EXPEDICIÓN DE TARJETA)"

# ================= TELEGRAM =================

class Telegram:

    def __init__(self):
        self.session = None

    async def init(self):

        if self.session is None:

            self.session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=120)
            )

    async def send(self, msg):

        await self.init()

        try:

            await self.session.post(
                f"{TG_URL}/sendMessage",
                data={
                    "chat_id": ADMIN_ID,
                    "text": str(msg)[:4000]
                }
            )

        except Exception as e:
            print("TG ERROR:", e)

    async def close(self):

        if self.session:
            await self.session.close()

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

def add_user(name, nie, phone, email, cities):

    cur.execute("""
        INSERT INTO users (name, nie, phone, email, cities)
        VALUES (?, ?, ?, ?, ?)
    """, (name, nie, phone, email, cities))

    conn.commit()

def get_users():

    cur.execute("""
        SELECT name, nie, phone, email, cities
        FROM users
        WHERE active=1
    """)

    return cur.fetchall()

# ================= SAFE GOTO =================

async def safe_goto(page, url):

    for i in range(5):

        try:

            print(f"🌐 GOTO attempt {i+1}")

            await page.goto(
                url,
                timeout=120000,
                wait_until="domcontentloaded"
            )

            await page.wait_for_selector(
                "select",
                state="visible",
                timeout=30000
            )

            return True

        except Exception as e:

            print("GOTO ERROR:", e)

            await asyncio.sleep(5)

    return False

# ================= CHECK =================

async def check(page, city):

    try:

        ok = await safe_goto(page, URL)

        if not ok:
            return None

        print(f"📍 Checking: {city}")

        await page.wait_for_timeout(2000)

        selects = page.locator("select")

        if await selects.count() == 0:
            return None

        try:
            await selects.nth(0).select_option(label=city)
        except:
            return None

        await page.click("input[type='submit']")

        await page.wait_for_load_state("networkidle")

        selects = page.locator("select")

        try:
            await selects.nth(0).select_option(label=SERVICE)
        except:
            return None

        await page.click("input[type='submit']")

        await page.wait_for_load_state("networkidle")

        html = (await page.content()).lower()

        patterns = [
            "no hay citas",
            "no existen citas",
            "en este momento no hay citas disponibles"
        ]

        if any(p in html for p in patterns):

            print(f"❌ No slots in {city}")

            return None

        print(f"🔥 FOUND in {city}")

        return page.url

    except Exception as e:

        print("CHECK ERROR:", e)

        return None

# ================= WORKER =================

running = False
worker_task = None

async def worker():

    global running

    print("🚀 WORKER STARTED")

    async with async_playwright() as p:

        browser = await p.chromium.launch(
            headless=True,
            proxy={
                "server": PROXY_SERVER,
                "username": PROXY_USER,
                "password": PROXY_PASS
            },
            args=[
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--disable-gpu"
            ]
        )

        context = await browser.new_context(
            locale="es-ES"
        )

        page = await context.new_page()

        await tg.send("🤖 BOT STARTED")

        while running:

            try:

                users = get_users()

                if not users:

                    print("⚠️ No users")

                    await asyncio.sleep(10)

                    continue

                for user in users:

                    name, nie, phone, email, cities = user

                    city_list = [
                        c.strip()
                        for c in cities.split(",")
                    ]

                    for city in city_list:

                        result = await check(page, city)

                        if result:

                            await tg.send(f"""
🔥 APPOINTMENT FOUND

👤 {name}
📍 {city}
🔗 {result}
""")

                            await asyncio.sleep(60)

                        await asyncio.sleep(3)

                await asyncio.sleep(10)

            except Exception as e:

                print("WORKER LOOP ERROR:", e)

                await asyncio.sleep(5)

        await browser.close()

# ================= COMMANDS =================

async def handle(text):

    global running
    global worker_task

    # ADD USER
    if text.startswith("/add"):

        try:

            parts = text.split("|")

            if len(parts) != 6:

                await tg.send(
                    "❌ Format:\n/add|name|nie|phone|email|cities"
                )

                return

            _, name, nie, phone, email, cities = parts

            add_user(
                name,
                nie,
                phone,
                email,
                cities
            )

            await tg.send("✅ User added")

        except Exception as e:

            await tg.send(f"❌ ADD ERROR: {e}")

    elif text == "/startbot":

        if worker_task and not worker_task.done():

            await tg.send("⚠️ Already running")

            return

        running = True

        worker_task = asyncio.create_task(worker())

        await tg.send("🚀 BOT STARTED")

    elif text == "/stopbot":

        running = False

        await tg.send("⛔ STOPPED")

# ================= MAIN =================

async def main():

    if not TOKEN:

        print("❌ TOKEN MISSING")

        return

    await tg.init()

    await tg.send("🤖 BOT ONLINE")

    offset = 0

    async with aiohttp.ClientSession(
        timeout=aiohttp.ClientTimeout(total=60)
    ) as s:

        while True:

            try:

                async with s.get(
                    f"{TG_URL}/getUpdates",
                    params={"offset": offset},
                ) as r:

                    data = await r.json()

                for upd in data.get("result", []):

                    offset = upd["update_id"] + 1

                    if "message" not in upd:
                        continue

                    chat_id = upd["message"]["chat"]["id"]

                    text = upd["message"].get("text", "")

                    if chat_id == ADMIN_ID:

                        await handle(text)

            except Exception as e:

                print("MAIN ERROR:", e)

            await asyncio.sleep(2)

if __name__ == "__main__":

    try:
        asyncio.run(main())

    except KeyboardInterrupt:
        print("STOPPED")
