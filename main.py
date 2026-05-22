import asyncio
import aiohttp
import os

TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = os.getenv("ADMIN_ID")

print("TOKEN =", TOKEN)
print("ADMIN =", ADMIN_ID)

if not TOKEN:
    print("❌ BOT_TOKEN is missing")
    exit()

TG_URL = f"https://api.telegram.org/bot{TOKEN}/sendMessage"

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

async def main():
    print("BOT STARTING...")

    await tg.init()

    print("TELEGRAM READY")

    await tg.send("Bot is running")

    while True:
        print("running...")
        await asyncio.sleep(60)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        print("CRASH:", e)
