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

CITIES = ["MADRID","BARCELONA","TOLEDO","ALICANTE","SEVILLA"]

SERVICE = "POLICÍA - TOMA DE HUELLAS (EXPEDICIÓN DE TARJETA)"

# ================= TELEGRAM =================

class Telegram:
    def __init__(self):
        self.session = None

    async def init(self):
        self.session = aiohttp.ClientSession()

    async def send(self, msg):
        if not self.session:
            await self.init()

        async with self.session.post(
            TG_URL,
            data={"chat_id": ADMIN_ID, "text": msg}
        ) as r:
            await r.text()

    async def close(self):
        if self.session:
            await self.session.close()

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

def add_user(name, nie, phone, email):
    cur.execute(
        "INSERT INTO users(name,nie,phone,email) VALUES(?,?,?,?)",
        (name, nie, phone, email)
    )
    conn.commit()

def get_users():
    cur.execute("SELECT name,nie,phone,email FROM users")
    return cur.fetchall()

def clear_users():
    cur.execute("DELETE FROM users")
    conn.commit()

# ================= STATE =================

user_state = {}

# ================= FORM HANDLER =================

async def handle(text, chat_id):

    if text == "/start":
        user_state[chat_id] = {"step": "name"}
        await tg.send("👤 اكتب الاسم ديالك:")
        return

    if text == "/reset":
        clear_users()
        user_state.clear()
        await tg.send("🗑 Database cleared")
        return

    if chat_id not in user_state:
        return

    step = user_state[chat_id]["step"]

    if step == "name":
        user_state[chat_id]["name"] = text
        user_state[chat_id]["step"] = "nie"
        await tg.send("📄 اكتب NIE:")

    elif step == "nie":
        user_state[chat_id]["nie"] = text
        user_state[chat_id]["step"] = "phone"
        await tg.send("📞 اكتب رقم الهاتف:")

    elif step == "phone":
        user_state[chat_id]["phone"] = text
        user_state[chat_id]["step"] = "email"
        await tg.send("📧 اكتب الإيميل:")

    elif step == "email":

        u = user_state[chat_id]

        add_user(u["name"], u["nie"], u["phone"], text)

        await tg.send(
            f"""✅ USER SAVED

👤 {u['name']}
📄 {u['nie']}
📞 {u['phone']}
📧 {text}

🤖 Monitoring started..."""
        )

        del user_state[chat_id]

# ================= PLAYWRIGHT =================

async def worker():

    async with async_playwright() as p:

        browser = await p.chromium.launch(
            headless=True,
            args=["--no-sandbox","--disable-setuid-sandbox"]
        )

        page = await browser.new_page()

        await tg.send("🤖 Playwright bot started on Railway")

        while True:

            users = get_users()

            for city in CITIES:
                for u in users:

                    try:
                        await page.goto(URL)

                        await page.locator("select").first.select_option(label=city)
                        await page.click("input[type='submit']")

                        await page.wait_for_load_state("domcontentloaded")

                        await page.locator("select").first.select_option(label=SERVICE)
                        await page.click("input[type='submit']")

                        html = await page.content()

                        if "no hay citas" not in html.lower():

                            await tg.send(
                                f"🔥 APPOINTMENT FOUND\n\n📍 {city}\n👤 {u[0]}\n📄 {u[1]}\n🔗 {URL}"
                            )

                        await asyncio.sleep(3)

                    except Exception as e:
                        print("ERROR:", e)

            await asyncio.sleep(10)

# ================= TELEGRAM LOOP =================

async def loop():

    offset = 0

    while True:

        async with aiohttp.ClientSession() as s:
            async with s.get(
                f"https://api.telegram.org/bot{TOKEN}/getUpdates",
                params={"offset": offset}
            ) as r:
                data = await r.json()

        for upd in data.get("result", []):

            offset = upd["update_id"] + 1

            if "message" in upd:
                chat_id = upd["message"]["
