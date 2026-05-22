import os
import asyncio
import sqlite3
import aiohttp
from playwright.async_api import async_playwright

# ================= CONFIG =================

TOKEN = os.getenv("8202293986:AAHL6nkd54h-D4_CTid6P9IQYcjj3nYQ9n8")
ADMIN_ID = int(os.getenv("6675176280"))

TG_URL = f"https://api.telegram.org/bot{TOKEN}/sendMessage"

URL = "https://icp.administracionelectronica.gob.es/icpplus/index.html"

CITIES = [
    "MADRID","BARCELONA","TOLEDO","ALICANTE",
    "SEVILLA","BILBAO","VALENCIA","GRANADA",
    "CORDOBA","MALAGA"
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
                data={
                    "chat_id": ADMIN_ID,
                    "text": msg
                }
            )
        except Exception as e:
            print("Telegram error:", e)

tg = Telegram()

# ================= DATABASE =================

conn = sqlite3.connect("users.db", check_same_thread=False)
cur = conn.cursor()

cur.execute("""
CREATE TABLE IF NOT EXISTS users(
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

def add_user(name, nie, phone, email):

    cur.execute(
        "INSERT INTO users(name,nie,phone,email) VALUES(?,?,?,?)",
        (name, nie, phone, email)
    )

    conn.commit()

def list_users():

    cur.execute(
        "SELECT name,nie FROM users WHERE active=1"
    )

    return cur.fetchall()

def get_users():

    cur.execute(
        "SELECT name,nie,phone,email FROM users WHERE active=1"
    )

    return cur.fetchall()

def delete_user(name):

    cur.execute(
        "DELETE FROM users WHERE name=?",
        (name,)
    )

    conn.commit()

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

        try:

            await page.fill(
                "input[name*='name'], input[type='text']",
                user[0]
            )

            await page.fill(
                "input[name*='nie']",
                user[1]
            )

            await page.fill(
                "input[name*='phone']",
                user[2]
            )

            await page.fill(
                "input[name*='email']",
                user[3]
            )

        except:
            pass

        return True

    except Exception as e:

        print("Check error:", e)

        return False

# ================= WORKER =================

running = False
worker_task = None

async def worker():

    global running

    async with async_playwright() as p:

        browser = await p.chromium.launch(
            headless=True,
            args=[
                "--disable-blink-features=AutomationControlled"
            ]
        )

        page = await browser.new_page()

        while running:

            users = get_users()

            for city in CITIES:

                for user in users:

                    found = await check(
                        page,
                        city,
                        user
                    )

                    if found:

                        await tg.send(
f"""🔥 APPOINTMENT FOUND

📍 City: {city}
👤 {user[0]}
📄 {user[1]}

⚠ Auto-filled
👉 Confirm manually"""
                        )

                        await asyncio.sleep(60)

                    await asyncio.sleep(2)

        await browser.close()

# ================= COMMANDS =================

async def handle(msg):

    global running
    global worker_task

    text = msg.strip()

    if text.startswith("/add"):

        parts = text.split(maxsplit=4)

        if len(parts) != 5:

            await tg.send(
                "Usage:\n/add NAME NIE PHONE EMAIL"
            )

            return

        _, name, nie, phone, email = parts

        add_user(
            name,
            nie,
            phone,
            email
        )

        await tg.send("✅ User added")

    elif text == "/list":

        users = list_users()

        if not users:

            await tg.send("No users")

            return

        await tg.send(
            "\n".join(
                [
                    f"{u[0]} - {u[1]}"
                    for u in users
                ]
            )
        )

    elif text.startswith("/del"):

        parts = text.split(maxsplit=1)

        if len(parts) != 2:

            return

        _, name = parts

        delete_user(name)

        await tg.send("🗑 Deleted")

    elif text == "/startbot":

        if running:

            await tg.send(
                "⚠ Bot already running"
            )

            return

        running = True

        worker_task = asyncio.create_task(
            worker()
        )

        await tg.send("🚀
