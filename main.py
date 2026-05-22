import asyncio
import sqlite3
import aiohttp
import os
from playwright.async_api import async_playwright

# ================= CONFIG =================

TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))

TG_URL = f"https://api.telegram.org/bot{TOKEN}/sendMessage"

URL = "https://icp.administracionelectronica.gob.es/icpplus/index.html"

CITIES = [
    "MADRID","BARCELONA","TOLEDO","ALICANTE","SEVILLA",
    "BILBAO","VALENCIA","GRANADA","CORDOBA","MALAGA"
]

SERVICE = "POLICÍA - TOMA DE HUELLAS (EXPEDICIÓN DE TARJETA)"

# ================= TELEGRAM =================

class Telegram:
    def __init__(self):
        self.session = None

    async def init(self):
        self.session = aiohttp.ClientSession()

    async def send(self, msg):
        await self.session.post(
            TG_URL,
            data={"chat_id": ADMIN_ID, "text": msg}
        )

tg = Telegram()

# ================= DB =================

conn = sqlite3.connect("users.db", check_same_thread=False)
cur = conn.cursor()

cur.execute("""
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT,
    nie TEXT,
    phone TEXT,
    email TEXT
)
""")
conn.commit()

def get_users():
    cur.execute("SELECT name,nie,phone,email FROM users")
    return cur.fetchall()

# ================= PLAYWRIGHT =================

async def check(page, city, user):

    try:
        await page.goto(URL, wait_until="domcontentloaded")

        await page.locator("select").first.select_option(label=city)
        await page.click("input[type='submit']")

        await page.wait_for_load_state("domcontentloaded")

        await page.locator("select").first.select_option(label=SERVICE)
        await page.click("input[type='submit']")

        html = await page.content()

        if "no hay citas" in html.lower():
            return False

        return True

    except Exception as e:
        print("CHECK ERROR:", e)
        return False

# ================= WORKER =================

async def worker():

    async with async_playwright() as p:

        browser = await p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-setuid-sandbox"]
        )

        page = await browser.new_page()

        await tg.send("🤖 Playwright bot started on Railway")

        while True:

            users = get_users()

            for city in CITIES:

                for user in users:

                    found = await check(page, city, user)

                    if found:
                        await tg.send(
                            f"""🔥 APPOINTMENT FOUND

📍 City: {city}
👤 {user[0]}
📄 {user[1]}

🔗 {URL}
"""
                        )
                        await asyncio.sleep(60)

                    await asyncio.sleep(2)

# ================= MAIN =================

async def main():
    await tg.init()
    await worker()

if __name__ == "__main__":
    asyncio.run(main())
