import asyncio
import sqlite3
import aiohttp
from playwright.async_api import async_playwright

# ================= CONFIG =================

TOKEN = "PUT_YOUR_BOT_TOKEN"
ADMIN_ID = 6675176280
TG_URL = f"https://api.telegram.org/bot{TOKEN}/sendMessage"

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
            await self.session.post(TG_URL, data={
                "chat_id": ADMIN_ID,
                "text": msg
            })
        except:
            pass

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
        INSERT INTO users(name,nie,phone,email,cities)
        VALUES(?,?,?,?,?)
    """, (name, nie, phone, email, cities))
    conn.commit()

def get_users():
    cur.execute("SELECT name,nie,phone,email,cities FROM users WHERE active=1")
    return cur.fetchall()

# ================= SAFE NAV =================

async def safe_goto(page, url):
    for _ in range(3):
        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=120000)
            return True
        except:
            await asyncio.sleep(2)
    return False

# ================= CHECK SYSTEM =================

async def check(page, city, user):

    try:
        ok = await safe_goto(page, URL)
        if not ok:
            return None

        # Step 1 city
        await page.locator("select").first.select_option(label=city)
        await page.click("input[type='submit']")
        await page.wait_for_load_state("domcontentloaded")

        # Step 2 service
        await page.locator("select").first.select_option(label=SERVICE)
        await page.click("input[type='submit']")
        await page.wait_for_load_state("domcontentloaded")

        html = await page.content()

        if "no hay citas" in html.lower():
            return None

        return page.url

    except:
        return None

# ================= WORKER =================

running = False

async def worker():

    async with async_playwright() as p:

        browser = await p.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--disable-blink-features=AutomationControlled"
            ]
        )

        page = await browser.new_page()

        await tg.send("🤖 Bot started successfully")

        while running:

            users = get_users()

            for user in users:

                name, nie, phone, email, cities = user
                city_list = [c.strip() for c in cities.split(",")]

                for city in city_list:

                    result = await check(page, city, user)

                    if result:

                        # Screenshot
                        try:
                            await page.screenshot(path="shot.png", full_page=True)

                            with open("shot.png", "rb") as f:
                                await tg.session.post(
                                    f"https://api.telegram.org/bot{TOKEN}/sendPhoto",
                                    data={
                                        "chat_id": ADMIN_ID,
                                        "caption": f"""
🔥 APPOINTMENT FOUND

👤 {name}
📄 {nie}
📞 {phone}
📧 {email}
📍 {city}

🔗 {result}

⚠️ Confirm manually
"""
                                    },
                                    files={"photo": f}
                                )
                        except:
                            await tg.send(f"🔥 FOUND (no screenshot)\n{result}")

                        await asyncio.sleep(60)

                    await asyncio.sleep(1)

# ================= COMMANDS =================

async def handle(text):

    global running

    if text.startswith("/add"):
        parts = text.split(" ", 5)

        if len(parts) < 6:
            await tg.send("❌ Format: /add name nie phone email cities")
            return

        _, name, nie, phone, email, cities = parts

        add_user(name, nie, phone, email, cities)
        await tg.send("✅ User added")

    elif text == "/startbot":
        running = True
        asyncio.create_task(worker())
        await tg.send("🚀 Bot started")

    elif text == "/stopbot":
        running = False
        await tg.send("⛔ Bot stopped")

# ================= MAIN LOOP =================

async def main():

    await tg.init()
    await tg.send("🤖 Admin bot ready")

    offset = None

    while True:

        async with aiohttp.ClientSession() as s:
            async with s.get(
                f"https://api.telegram.org/bot{TOKEN}/getUpdates?offset={offset}"
            ) as r:
                data = await r.json()

        for upd in data.get("result", []):

            offset = upd["update_id"] + 1

            if "message" in upd:
                chat_id = upd["message"]["chat"]["id"]
                text = upd["message"].get("text", "")

                if chat_id == ADMIN_ID:
                    await handle(text)

        await asyncio.sleep(2)

if __name__ == "__main__":
    asyncio.run(main())
