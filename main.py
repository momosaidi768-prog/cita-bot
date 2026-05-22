import asyncio
import sqlite3
import aiohttp
import os

TOKEN = "PUT_YOUR_BOT_TOKEN"
ADMIN_ID = 6675176280

TG_URL = f"https://api.telegram.org/bot{TOKEN}/sendMessage"

BOOKING_URL = "https://icp.administracionelectronica.gob.es/icpplus/index.html"

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

# ================= STATE (form) =================

user_state = {}

# ================= HANDLER =================

async def handle(text):

    global user_state

    # start form
    if text == "/start":
        user_state["step"] = "name"
        await tg.send("👤 اكتب الاسم ديالك:")

    elif "step" in user_state:

        step = user_state["step"]

        if step == "name":
            user_state["name"] = text
            user_state["step"] = "nie"
            await tg.send("📄 اكتب NIE:")

        elif step == "nie":
            user_state["nie"] = text
            user_state["step"] = "phone"
            await tg.send("📞 اكتب رقم الهاتف:")

        elif step == "phone":
            user_state["phone"] = text
            user_state["step"] = "email"
            await tg.send("📧 اكتب الإيميل:")

        elif step == "email":
            user_state["email"] = text

            # save
            cur.execute(
                "INSERT INTO users(name,nie,phone,email) VALUES(?,?,?,?)",
                (user_state["name"], user_state["nie"],
                 user_state["phone"], user_state["email"])
            )
            conn.commit()

            # final message
            await tg.send(
                "✅ تم حفظ المعلومات\n\n"
                f"👤 {user_state['name']}\n"
                f"📄 {user_state['nie']}\n"
                f"📞 {user_state['phone']}\n"
                f"📧 {user_state['email']}\n\n"
                f"🔗 رابط الحجز:\n{BOOKING_URL}\n\n"
                "👉 دير الحجز يدويًا واضغط confirm"
            )

            user_state = {}

# ================= MAIN =================

async def main():

    await tg.init()
    print("Bot started")

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
                text = upd["message"].get("text", "")
                await handle(text)

        await asyncio.sleep(2)

if __name__ == "__main__":
    asyncio.run(main())
