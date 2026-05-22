import asyncio
import sqlite3
import aiohttp
from playwright.async_api import async_playwright

# ================= CONFIG =================

TOKEN = "PUT_YOUR_BOT_TOKEN"
ADMIN_ID = 6675176280

TG_URL = f"https://api.telegram.org/bot{TOKEN}"

URL = "https://icp.administracionelectronica.gob.es/icpplus/index.html"

SERVICE = "POLICÍA - TOMA DE HUELLAS (EXPEDICIÓN DE TARJETA)"

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
            await self.session.post(
                f"{TG_URL}/sendMessage",
                data={
                    "chat_id": ADMIN_ID,
                    "text": msg
                }
            )
        except Exception as e:
            print("SEND ERROR:", e)

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

# ================= USERS =================

def add_user(name, nie, phone, email, cities):

    cur.execute("""
        INSERT INTO users(name,nie,phone,email,cities)
        VALUES(?,?,?,?,?)
    """, (name, nie, phone, email, cities))

    conn.commit()

def get_users():

    cur.execute("""
        SELECT name,nie,phone,email,cities
        FROM users
        WHERE active=1
    """)

    return cur.fetchall()

# ================= SAFE GOTO =================

async def safe_goto(page, url):

    for _ in range(3):

        try:

            await page.goto(
                url,
                wait_until="domcontentloaded",
                timeout=120000
            )

            return True

        except Exception as e:

            print("GOTO ERROR:", e)

            await asyncio.sleep(3)

    return False

# ================= CHECK =================

async def check(page, city):

    try:

        ok = await safe_goto(page, URL)

        if not ok:
            return None

        print(f"📍 Checking city: {city}")

        # STEP 1
        await page.locator("select").first.select_option(label=city)

        await page.click("input[type='submit']")

        await page.wait_for_load_state("domcontentloaded")

        # STEP 2
        await page.locator("select").first.select_option(label=SERVICE)

        await page.click("input[type='submit']")

        await page.wait_for_load_state("domcontentloaded")

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

async def worker():

    global running

    try:

        async with async_playwright() as p:

            print("🚀 STARTING BROWSER...")

            browser = await p.chromium.launch(
                channel="chromium",
                headless=True,
                timeout=120000,
                args=[
                    "--no-sandbox",
                    "--disable-setuid-sandbox",
                    "--disable-dev-shm-usage",
                    "--disable-gpu",
                    "--disable-blink-features=AutomationControlled"
                ]
            )

            print("✅ BROWSER STARTED")

            page = await browser.new_page()

            await tg.send("🤖 Bot started successfully")

            while running:

                users = get_users()

                for user in users:

                    name, nie, phone, email, cities = user

                    city_list = [c.strip() for c in cities.split(",")]

                    for city in city_list:

                        result = await check(page, city)

                        if result:

                            try:

                                # SCREENSHOT
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

⚠️ Confirm manually
"""
                                )

                                form.add_field(
                                    "photo",
                                    open("shot.png", "rb"),
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
                                    f"🔥 FOUND\n\n📍 {city}\n🔗 {result}"
                                )

                            await asyncio.sleep(60)

                        await asyncio.sleep(2)

    except Exception as e:

        print("WORKER ERROR:", e)

        await tg.send(f"❌ WORKER ERROR:\n{e}")

# ================= COMMANDS =================

async def handle(text):

    global running

    if text.startswith("/add"):

        parts = text.split(" ", 5)

        if len(parts) < 6:

            await tg.send(
                "❌ Format:\n/add name nie phone email cities"
            )

            return

        _, name, nie, phone, email, cities = parts

        add_user(name, nie, phone, email, cities)

        await tg.send("✅ User added")

    elif text == "/startbot":

        if running:
            await tg.send("⚠️ Bot already running")
            return

        running = True

        asyncio.create_task(worker())

        await tg.send("🚀 Bot started")

    elif text == "/stopbot":

        running = False

        await tg.send("⛔ Bot stopped")

# ================= MAIN =================

async def main():

    print("🔥 BOT STARTING...")

    await tg.init()

    await tg.send("🤖 ADMIN BOT READY")

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

                    text = upd["message"].get("text", "")

                    if chat_id == ADMIN_ID:

                        await handle(text)

        except Exception as e:

            print("MAIN LOOP ERROR:", e)

        await asyncio.sleep(2)

# ================= START =================

if __name__ == "__main__":

    asyncio.run(main())
