import asyncio
import sqlite3
import aiohttp
import os

from playwright.async_api import async_playwright

# ================= CONFIG =================

TOKEN = os.getenv("BOT_TOKEN")

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

            async with self.session.post(
                f"{TG_URL}/sendMessage",
                data={
                    "chat_id": ADMIN_ID,
                    "text": str(msg)[:4000]
                }
            ) as r:

                if r.status != 200:
                    print("TG ERROR:", await r.text())

        except Exception as e:
            print("TG ERROR:", e)

    async def close(self):

        if self.session:
            await self.session.close()

tg = Telegram()

# ================= DATABASE =================

conn = sqlite3.connect(
    "users.db",
    check_same_thread=False
)

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
        INSERT INTO users (
            name,
            nie,
            phone,
            email,
            cities
        )
        VALUES (?, ?, ?, ?, ?)
    """, (
        name,
        nie,
        phone,
        email,
        cities
    ))

    conn.commit()

def get_users():

    cur.execute("""
        SELECT
            name,
            nie,
            phone,
            email,
            cities
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
                timeout=30000
            )

            return True

        except Exception as e:

            print("GOTO ERROR:", e)

            await asyncio.sleep(5)

    return False

# ================= CHECK =================

async def check(context, city):

    page = await context.new_page()

    try:

        ok = await safe_goto(page, URL)

        if not ok:
            await page.close()
            return None

        print(f"📍 Checking: {city}")

        await page.wait_for_timeout(3000)

        selects = page.locator("select")

        count = await selects.count()

        if count == 0:

            print("❌ No select found")

            await page.close()
            return None

        # ================= CITY =================

        try:

            options = await selects.nth(0).locator(
                "option"
            ).all_text_contents()

            print("AVAILABLE CITIES:", options)

            found = False

            for op in options:

                if city.lower().strip() in op.lower():

                    await selects.nth(0).select_option(
                        label=op
                    )

                    found = True
                    break

            if not found:

                print(f"❌ City not found: {city}")

                await page.close()
                return None

        except Exception as e:

            print("CITY ERROR:", e)

            await page.close()
            return None

        # NEXT

        await page.click("input[type='submit']")

        await page.wait_for_load_state("networkidle")

        await page.wait_for_timeout(2000)

        # ================= SERVICE =================

        selects = page.locator("select")

        try:

            options = await selects.nth(0).locator(
                "option"
            ).all_text_contents()

            found = False

            for op in options:

                if SERVICE.lower() in op.lower():

                    await selects.nth(0).select_option(
                        label=op
                    )

                    found = True
                    break

            if not found:

                print("❌ SERVICE NOT FOUND")

                await page.close()
                return None

        except Exception as e:

            print("SERVICE ERROR:", e)

            await page.close()
            return None

        # NEXT

        await page.click("input[type='submit']")

        await page.wait_for_load_state("networkidle")

        await page.wait_for_timeout(3000)

        html = (await page.content()).lower()

        patterns = [
            "no hay citas",
            "no existen citas",
            "en este momento no hay citas disponibles"
        ]

        if any(p in html for p in patterns):

            print(f"❌ No slots in {city}")

            await page.close()
            return None

        print(f"🔥 FOUND in {city}")

        current_url = page.url

        await page.close()

        return current_url

    except Exception as e:

        print("CHECK ERROR:", e)

        try:
            await page.close()
        except:
            pass

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
                "--disable-blink-features=AutomationControlled",
                "--disable-gpu"
            ]
        )

        context = await browser.new_context(
            locale="es-ES",
            viewport={
                "width": 1366,
                "height": 768
            },
            user_agent=(
                "Mozilla/5.0 "
                "(Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 "
                "(KHTML, like Gecko) "
                "Chrome/122.0.0.0 Safari/537.36"
            )
        )

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
                        if c.strip()
                    ]

                    for city in city_list:

                        result = await check(
                            context,
                            city
                        )

                        if result:

                            await tg.send(f"""
🔥 APPOINTMENT FOUND

👤 {name}
📍 {city}

🔗 {result}
""")

                            await asyncio.sleep(60)

                        await asyncio.sleep(5)

                await asyncio.sleep(15)

            except Exception as e:

                print("WORKER LOOP ERROR:", e)

                await asyncio.sleep(10)

        await browser.close()

# ================= COMMANDS =================

async def handle(text):

    global running
    global worker_task

    # ================= ADD USER =================

    if text.startswith("/add"):

        try:

            parts = text.split("|")

            if len(parts) != 6:

                await tg.send(
                    "❌ FORMAT:\n"
                    "/add|name|nie|phone|email|cities"
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

            await tg.send("✅ USER ADDED")

        except Exception as e:

            await tg.send(f"❌ ADD ERROR:\n{e}")

    # ================= START BOT =================

    elif text == "/startbot":

        if worker_task and not worker_task.done():

            await tg.send("⚠️ ALREADY RUNNING")
            return

        running = True

        worker_task = asyncio.create_task(
            worker()
        )

        await tg.send("🚀 BOT STARTED")

    # ================= STOP BOT =================

    elif text == "/stopbot":

        running = False

        await tg.send("⛔ BOT STOPPED")

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
                    params={
                        "offset": offset,
                        "timeout": 30
                    }
                ) as r:

                    data = await r.json()

                for upd in data.get("result", []):

                    offset = upd["update_id"] + 1

                    if "message" not in upd:
                        continue

                    chat_id = upd["message"]["chat"]["id"]

                    text = upd["message"].get(
                        "text",
                        ""
                    )

                    print("MESSAGE:", text)

                    if chat_id == ADMIN_ID:

                        await handle(text)

            except Exception as e:

                print("MAIN ERROR:", e)

            await asyncio.sleep(2)

# ================= START =================

if __name__ == "__main__":

    try:

        asyncio.run(main())

    except KeyboardInterrupt:

        print("⛔ STOPPED")
