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
        try:
            if not self.session:
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

# ================= SAFE GOTO =================

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
            await asyncio.sleep(5)
    return False

# ================= WORKER =================

async def worker():

    async with async_playwright() as p:

        browser = await p.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-setuid-sandbox
