import asyncio
import aiohttp
import sqlite3
import os
from playwright.async_api import async_playwright

TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))

TG_URL = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
URL = "https://icp.administracionelectronica.gob.es/icpplus/index.html"

CITIES = ["MADRID", "BARCELONA", "SEVILLA"]

SERVICE = "POLICÍA - TOMA DE HUELLAS"

# ================= TELEGRAM =================

class Telegram:
    def __init__(self):
        self.session = None

    async def init(self):
        self.session = aiohttp.ClientSession()

    async def send(self, msg):
        if not self.session:
            await self.init()

        try:
            async with self.session.post(
                TG_URL,
                data={"chat_id": ADMIN_ID, "text": msg}
            ):
                pass
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
            print(f"[NAV RETRY {i+1}] {e}")
            await asyncio.sleep(5)
    return False

# ================= WORKER =================

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

        page.set_default_timeout(60000)
        page.set_default_navigation_timeout(120000)

        await tg.send("🤖 PRO Bot started")

        while True:

            users = get_users()

            for city in CITIES:
                for u in users:

                    ok = await safe_goto(page, URL)

                    if not ok:
                        continue

                    try:
                        await page.locator("select").first.select_option(label=city)
                        await page.click("input[type='submit']")
                        await page.wait_for_load_state("domcontentloaded")

                        await page.locator("select").first.select_option(label=SERVICE)
                        await page.click("input[type='submit']")

                        html = await page.content()

                        if "no hay citas" not in html.lower():

                            await tg.send(
                                f"🔥 APPOINTMENT FOUND\n📍 {city}\n👤 {u[0]}\n📄 {u[1]}"
                            )

                        await asyncio.sleep(3)

                    except Exception as e:
                        print("ERROR:", e)

            await asyncio.sleep(8)

# ================= MAIN =================

async def main():
    await tg.init()
    await worker()

if __name__ == "__main__":
    asyncio.run(main())
