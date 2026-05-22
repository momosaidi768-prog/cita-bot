import asyncio
import sqlite3
import aiohttp
from playwright.async_api import async_playwright

# ================= CONFIG =================

TOKEN = "PUT_YOUR_BOT_TOKEN"
ADMIN_ID = 6675176280

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
        if not self.session:
            self.session = aiohttp.ClientSession()

    async def send(self, msg):
        try:
            await self.init()
            await self.session.post(
                TG_URL,
                data={"chat_id": ADMIN_ID, "text": msg}
            )
        except Exception as e:
            print("Telegram error:", e)

tg = Telegram()

# ================= DB =================

conn = sqlite3.connect("users.db", check_same_thread=False)
cur = conn.cursor()

cur.execute("""
CREATE TABLE IF NOT EXISTS users (
    name TEXT,
    nie TEXT,
    phone TEXT,
    email TEXT
)
""")
conn.commit()

def get_users():
    cur.execute("SELECT * FROM users")
    return cur.fetchall()

# ================= SAFE NAV =================

async def safe_goto(page, url):
    for i in range(5):
        try:
            await page.goto(
                url,
                wait_until="domcontentloaded",
                timeout=120000
            )
            return True
        except Exception as e:
            print(f"[RETRY {i+1}] {e}")
            await asyncio.sleep(3)
    return False

# ================= CHECK =================

async def check(page, city, user):

    try:
        ok = await safe_goto(page, URL)
        if not ok:
            return False

        await page.locator("select").first.select_option(label=city)
        await page.click("input[type='submit']")
        await page.wait_for_load_state("domcontentloaded")

        await page.locator("select").first.select_option(label=SERVICE)
        await page.click("input[type='submit']")
        await page.wait_for_load_state("domcontentloaded")

        html = await page.content()

        if "no hay citas" in html.lower():
            return False

        return True

    except Exception as e:
        print("CHECK ERROR:", e)
        return False

# ================= WORKER =================

running = True

async def worker():

    async with async_playwright() as p:

        browser = await p.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-dev-shm-usage"
            ]
        )

        page = await browser.new_page()

        await tg.send("🤖 BOT STARTED (FIXED VERSION)")

        while running:

            users = get_users()

            for city in CITIES:

                # 🔔 إشعار كل مدينة
                await tg.send(f"🔍 Checking city: {city}")

                for u in users:

                    found = await check(page, city, u)

                    if found:
                        await tg.send(
                            f"🔥 APPOINTMENT FOUND\n\n📍 {city}\n👤 {u[0]}\n📄 {u[1]}"
                        )
                        await asyncio.sleep(60)

                    await asyncio.sleep(2)

# ================= MAIN =================

async def main():

    await tg.init()
    await tg.send("🤖 Telegram bot ready")

    await worker()

# ================= START =================

if __name__ == "__main__":
    asyncio.run(main())
