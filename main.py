import asyncio
import sqlite3
import aiohttp
import os
from playwright.async_api import async_playwright

# ================= CONFIG =================

TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))

if not TOKEN:
    print("❌ BOT_TOKEN missing")
    exit()

TG_URL = f"https://api.telegram.org/bot{TOKEN}/sendMessage"

URL = "https://icp.administracionelectronica.gob.es/icpplus/index.html"

CITIES = [
    "MADRID",
    "BARCELONA",
    "TOLEDO",
    "ALICANTE",
    "SEVILLA",
    "BILBAO",
    "VALENCIA",
    "GRANADA",
    "CORDOBA",
    "MALAGA"
]

SERVICE = "POLICÍA - TOMA DE HUELLAS (EXPEDICIÓN DE TARJETA)"

# ================= TELEGRAM =================

class Telegram:

    def __init__(self):
        self.session = None

    async def init(self):
        self.session = aiohttp.ClientSession()

    async def send(self, msg):

        if self.session is None:
            await self.init()

        try:
            async with self.session.post(
                TG_URL,
                data={
                    "chat_id": ADMIN_ID,
                    "text": msg
                }
            ) as r:
                await r.text()

        except Exception as e:
            print("TELEGRAM ERROR:", e)

    async def close(self):
        if self.session:
            await self.session.close()

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

def add_user(name, nie, phone, email):

    cur.execute(
        "INSERT INTO users(name,nie,phone,email) VALUES(?,?,?,?)",
        (name, nie, phone, email)
    )

    conn.commit()

def get_users():

    cur.execute(
        "SELECT name,nie,phone,email FROM users WHERE active=1"
    )

    return cur.fetchall()

# ================= USER FORM =================

user_state = {}

# ================= PLAYWRIGHT CHECK =================

async def check(page, city, user):

    try:

        print(f"Checking {city} for {user[0]}")

        await page.goto(URL, wait_until="domcontentloaded")

        await page.locator("select").first.select_option(label=city)

        await page.click("input[type='submit']")

        await page.wait_for_load_state("domcontentloaded")

        await page.locator("select").first.select_option(label=SERVICE)

        await page.click("input[type='submit']")

        await page.wait_for_load_state("domcontentloaded")

        html = await page.content()

        if "no hay citas" in html.lower():

            print(f"No citas in {city}")

            return False

        print(f"🔥 APPOINTMENT FOUND IN {city}")

        return True

    except Exception as e:

        print("CHECK ERROR:", e)

        return False

# ================= PLAYWRIGHT WORKER =================

async def worker():

    while True:

        try:

            async with async_playwright() as p:

                browser = await p.chromium.launch(
                    headless=True,
                    args=[
                        "--no-sandbox",
                        "--disable-setuid-sandbox"
                    ]
                )

                page = await browser.new_page()

                await tg.send("🤖 Playwright bot started on Railway")

                while True:

                    users = get_users()

                    if not users:
                        print("No users in database")

                    for city in CITIES:

                        for user in users:

                            found = await check(page, city, user)

                            if found:

                                await tg.send(
                                    f"""
🔥 APPOINTMENT FOUND

📍 City: {city}

👤 {user[0]}
📄 {user[1]}

🔗 {URL}

👉 Open the link and confirm manually
"""
                                )

                                await asyncio.sleep(60)

                            await asyncio.sleep(3)

        except Exception as e:

            print("WORKER ERROR:", e)

            await asyncio.sleep(10)

# ================= COMMAND HANDLER =================

async def handle(text, chat_id):

    global user_state

    # START
    if text == "/start":

        user_state[chat_id] = {
            "step": "name"
        }

        await tg.send("👤 اكتب الاسم ديالك:")

    # LIST USERS
    elif text == "/list":

        users = get_users()

        if not users:
            await tg.send("❌ No users")

        else:

            msg = "📋 USERS:\n\n"

            for u in users:
                msg += f"👤 {u[0]} - {u[1]}\n"

            await tg.send(msg)

    # FORM PROCESS
    elif chat_id in user_state:

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

            user_state[chat_id]["email"] = text

            u = user_state[chat_id]

            add_user(
                u["name"],
                u["nie"],
                u["phone"],
                u["email"]
            )

            await tg.send(
                f"""
✅ USER SAVED

👤 {u['name']}
📄 {u['nie']}
📞 {u['phone']}
📧 {u['email']}

🤖 Monitoring appointments now...
"""
            )

            del user_state[chat_id]

# ================= TELEGRAM LOOP =================

async def telegram_loop():

    offset = 0

    while True:

        try:

            async with aiohttp.ClientSession() as s:

                async with s.get(
                    f"https://api.telegram.org/bot{TOKEN}/getUpdates",
                    params={"offset": offset}
                ) as r:

                    data = await r.json()

            for upd in data.get("result", []):

                offset = upd["update_id"] + 1

                if "message" in upd:

                    chat_id = upd["message"]["chat"]["id"]
                    text = upd["message"].get("text", "")

                    if chat_id == ADMIN_ID:
                        await handle(text, chat_id)

        except Exception as e:

            print("TELEGRAM LOOP ERROR:", e)

        await asyncio.sleep(2)

# ================= MAIN =================

async def main():

    print("🚀 BOT STARTING...")

    await tg.init()

    await tg.send("✅ Bot started successfully on Railway")

    await asyncio.gather(
        telegram_loop(),
        worker()
    )

# ================= START =================

if __name__ == "__main__":

    try:
        asyncio.run(main())

    finally:

        try:
            asyncio.run(tg.close())
        except:
            pass
