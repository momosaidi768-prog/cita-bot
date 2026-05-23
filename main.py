import asyncio
import sqlite3
import aiohttp
import os
from playwright.async_api import async_playwright

# ================= CONFIG =================

TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = 6675176280

TG_URL = f"https://api.telegram.org/bot{TOKEN}"

URL = "https://icp.administracionelectronica.gob.es/icpplus/index.html"

SERVICE = "POLICÍA - TOMA DE HUELLAS (EXPEDICIÓN DE TARJETA)"

# ================= TELEGRAM =================

class Telegram:

    def __init__(self):
        self.session = None

    async def init(self):

        if self.session is None:

            timeout = aiohttp.ClientTimeout(total=120)

            self.session = aiohttp.ClientSession(
                timeout=timeout
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

                await r.text()

        except Exception as e:

            print("SEND ERROR:", e)

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

# ================= USERS =================

def add_user(name, nie, phone, email, cities):

    cur.execute(
        """
        INSERT INTO users
        (name, nie, phone, email, cities)
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            name,
            nie,
            phone,
            email,
            cities
        )
    )

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

    for attempt in range(3):

        try:

            await page.goto(
                url,
                wait_until="domcontentloaded",
                timeout=120000
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

        print(f"📍 Checking city: {city}")

        selects = page.locator("select")

        count = await selects.count()

        if count < 1:
            return None

        # STEP 1 CITY

        try:

            await selects.nth(0).select_option(
                label=city
            )

        except Exception as e:

            print("CITY ERROR:", e)

            return None

        await page.click("input[type='submit']")

        await page.wait_for_load_state(
            "domcontentloaded"
        )

        # STEP 2 SERVICE

        selects = page.locator("select")

        try:

            await selects.nth(0).select_option(
                label=SERVICE
            )

        except Exception as e:

            print("SERVICE ERROR:", e)

            return None

        await page.click("input[type='submit']")

        await page.wait_for_load_state(
            "domcontentloaded"
        )

        html = await page.content()

        if "no hay citas" in html.lower():

            print(f"❌ No appointments in {city}")

            return None

        print(f"🔥 APPOINTMENT FOUND IN {city}")

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

    try:

        async with async_playwright() as p:

            browser = await p.chromium.launch(
                headless=True,
                args=[
                    "--no-sandbox",
                    "--disable-setuid-sandbox",
                    "--disable-dev-shm-usage",
                    "--disable-gpu",
                    "--single-process",
                    "--disable-blink-features=AutomationControlled"
                ]
            )

            print("✅ BROWSER STARTED")

            context = await browser.new_context()

            page = await context.new_page()

            await tg.send("🤖 Bot started")

            while running:

                users = get_users()

                if not users:

                    print("⚠️ No users in database")

                    await asyncio.sleep(10)

                    continue

                for user in users:

                    try:

                        name, nie, phone, email, cities = user

                        city_list = [
                            c.strip()
                            for c in cities.split(",")
                        ]

                        for city in city_list:

                            result = await check(
                                page,
                                city
                            )

                            if result:

                                try:

                                    await page.screenshot(
                                        path="shot.png",
                                        full_page=True
                                    )

                                    form = aiohttp.FormData()

                                    form.add_field(
                                        "chat_id",
                                        str(ADMIN_ID)
                                    )

                                    form.add_field(
                                        "caption",
                                        f"""
🔥 APPOINTMENT FOUND

👤 {name}
📄 {nie}
📞 {phone}
📧 {email}
📍 {city}

🔗 {result}
"""
                                    )

                                    form.add_field(
                                        "photo",
                                        open(
                                            "shot.png",
                                            "rb"
                                        ),
                                        filename="shot.png",
                                        content_type="image/png"
                                    )

                                    await tg.session.post(
                                        f"{TG_URL}/sendPhoto",
                                        data=form
                                    )

                                    print("📸 Screenshot sent")

                                except Exception as e:

                                    print("PHOTO ERROR:", e)

                                    await tg.send(
                                        f"""
🔥 APPOINTMENT FOUND

📍 {city}

🔗 {result}
"""
                                    )

                                await asyncio.sleep(60)

                            await asyncio.sleep(3)

                    except Exception as e:

                        print("USER ERROR:", e)

                await asyncio.sleep(10)

            await browser.close()

    except Exception as e:

        print("WORKER ERROR:", e)

        await tg.send(
            f"❌ WORKER ERROR:\n{str(e)[:500]}"
        )

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
                    """
❌ Format:

/add|name|nie|phone|email|cities
"""
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

            await tg.send(
                f"❌ ADD ERROR:\n{e}"
            )

    # START BOT

    elif text == "/startbot":

        if running:

            await tg.send(
                "⚠️ Bot already running"
            )

            return

        running = True

        worker_task = asyncio.create_task(
            worker()
        )

        await tg.send("🚀 Bot started")

    # STOP BOT

    elif text == "/stopbot":

        running = False

        if worker_task:
            worker_task.cancel()

        await tg.send("⛔ Bot stopped")

    # LIST USERS

    elif text == "/users":

        users = get_users()

        if not users:

            await tg.send("⚠️ No users")

            return

        msg = "👥 USERS:\n\n"

        for user in users:

            name, nie, phone, email, cities = user

            msg += f"""
👤 {name}
📄 {nie}
📍 {cities}

"""

        await tg.send(msg)

# ================= MAIN =================

async def main():

    print("🔥 BOT STARTING...")

    if not TOKEN:

        print("❌ BOT TOKEN NOT FOUND")

        return

    await tg.init()

    await tg.send("🤖 BOT ONLINE")

    offset = None

    while True:

        try:

            async with aiohttp.ClientSession() as s:

                async with s.get(
                    f"{TG_URL}/getUpdates?offset={offset}",
                    timeout=120
                ) as r:

                    data = await r.json()

            for upd in data.get("result", []):

                offset = upd["update_id"] + 1

                if "message" in upd:

                    chat_id = upd["message"]["chat"]["id"]

                    text = upd["message"].get(
                        "text",
                        ""
                    )

                    if chat_id == ADMIN_ID:

                        await handle(text)

        except Exception as e:

            print("MAIN LOOP ERROR:", e)

        await asyncio.sleep(2)

# ================= START =================

if __name__ == "__main__":

    asyncio.run(main())
