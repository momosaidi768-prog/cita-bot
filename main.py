import asyncio
import sqlite3
import aiohttp
import os
from playwright.async_api import async_playwright

# ================= CONFIG =================

TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))

if not TOKEN:
    print("❌ BOT_TOKEN missing")
    exit()

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
        try:
            await self.session.post(
                TG_URL,
                data={"chat_id": ADMIN_ID, "text": msg}
            )
        except Exception as e:
            print("Telegram error:", e)

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
    active INTEGER DEFAULT 1
)
""")
conn.commit()

# ================= USERS =================

def get_users():
    cur.execute("SELECT name,nie,phone,email FROM users WHERE active=1")
    return cur.fetchall()

def add_user(name, nie, phone, email):
    cur.execute(
        "INSERT INTO users(name,nie,phone,email) VALUES(?,?,?,?)",
        (name, nie, phone, email)
    )
    conn.commit()

def delete_user(name):
    cur.execute("DELETE FROM users WHERE name=?", (name,))
    conn.commit()

def list_users():
    cur.execute("SELECT name,nie FROM users WHERE active=1")
    return cur.fetchall()

# ================= PLAYWRIGHT =================

async def check(page, city, user):
    try:
        await page.goto(URL, timeout=60000)
        await page.wait_for_load_state("domcontentloaded")

        selects = page.locator("select")
        await selects.first.select_option(label=city)

        await page.click("input[type='submit']")
        await page.wait_for_load_state("domcontentloaded")

        selects = page.locator("select")
        await selects.first.select_option(label=SERVICE)

        await page.click("input[type='submit']")
        await page.wait_for_load_state("domcontentloaded")

        html = await page.content()

        if "no hay citas" in html.lower():
            return False

        return True

    except Exception as e:
        print("Playwright error:", e)
        return False

# ================= WORKER =================

running = False

async def worker():
    global running

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        while running:
            users = get_users()

            for city in CITIES:
                for user in users:

                    found = await check(page, city, user)

                    if found:
                        await tg.send(
                            f"🔥 APPOINTMENT FOUND\n📍 {city}\n👤 {user[0]}\n📄 {user[1]}"
                        )
                        await asyncio.sleep(60)

                    await asyncio.sleep(2)

# ================= BOT (GETUPDATES SAFE) =================

offset = None
session = None

async def main():
    global offset, session, running

    print("BOT STARTING...")

    session = aiohttp.ClientSession()
    await tg.init()

    await tg.send("🤖 Bot ready")

    while True:
        try:
            async with session.get(
                f"https://api.telegram.org/bot{TOKEN}/getUpdates",
                params={"offset": offset, "timeout": 10}
            ) as r:
                data = await r.json()

            for upd in data.get("result", []):

                offset = upd["update_id"] + 1

                if "message" in upd:
                    text = upd["message"].get("text", "")
                    chat_id = upd["message"]["chat"]["id"]

                    if chat_id == ADMIN_ID:
                        await handle(text)

        except Exception as e:
            print("Loop error:", e)

        await asyncio.sleep(1)

# ================= COMMANDS =================

async def handle(text):
    global running

    try:
        if text.startswith("/add"):
            _, name, nie, phone, email = text.split(" ")
            add_user(name, nie, phone, email)
            await tg.send("✅ User added")

        elif text.startswith("/list"):
            users = list_users()
            await tg.send("\n".join([f"{u[0]} - {u[1]}" for u in users]))

        elif text.startswith("/del"):
            _, name = text.split(" ")
            delete_user(name)
            await tg.send("🗑 Deleted")

        elif text == "/startbot":
            if not running:
                running = True
                asyncio.create_task(worker())
                await tg.send("🚀 Bot started")

        elif text == "/stopbot":
            running = False
            await tg.send("⛔ Bot stopped")

    except Exception as e:
        await tg.send(f"❌ Error: {e}")

# ================= RUN =================

if __name__ == "__main__":
    asyncio.run(main())
