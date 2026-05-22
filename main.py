
import asyncio
import sqlite3
import aiohttp
from playwright.async_api import async_playwright

# ================= CONFIG =================

TOKEN = "8202293986:AAHL6nkd54h-D4_CTid6P9IQYcjj3nYQ9n8"
ADMIN_ID = 6675176280

TG_URL = f"https://api.telegram.org/bot{TOKEN}/sendMessage"

URL = "https://icp.administracionelectronica.gob.es/icpplus/index.html"

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
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT,
    nie TEXT,
    phone TEXT,
    email TEXT,
    city TEXT,
    active INTEGER DEFAULT 1
)
""")

conn.commit()

# ================= USERS =================

def add_user(name, nie, phone, email, city):

    cur.execute("""
    INSERT INTO users(name,nie,phone,email,city)
    VALUES(?,?,?,?,?)
    """, (name, nie, phone, email, city.upper()))

    conn.commit()


def list_users():

    cur.execute("""
    SELECT name,nie,city
    FROM users
    WHERE active=1
    """)

    return cur.fetchall()


def get_users():

    cur.execute("""
    SELECT name,nie,phone,email,city
    FROM users
    WHERE active=1
    """)

    return cur.fetchall()


def delete_user(nie):

    cur.execute("""
    DELETE FROM users
    WHERE nie=?
    """, (nie,))

    conn             "
