import os
import aiohttp
import asyncio

TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = os.getenv("ADMIN_ID")

TG_URL = f"https://api.telegram.org/bot{TOKEN}/sendMessage"

async def send(msg):
    async with aiohttp.ClientSession() as s:
        await s.post(TG_URL, data={
            "chat_id": ADMIN_ID,
            "text": msg
        })

async def main():
    await send("🤖 Test bot is running!")

    offset = None

    while True:
        try:
            async with aiohttp.ClientSession() as s:
                url = f"https://api.telegram.org/bot{TOKEN}/getUpdates"
                async with s.get(url, params={"offset": offset}) as r:
                    data = await r.json()

            for upd in data.get("result", []):
                offset = upd["update_id"] + 1

                if "message" in upd:
                    text = upd["message"]["text"]

                    await send(f"📩 Echo: {text}")

        except Exception as e:
            print("error:", e)

        await asyncio.sleep(2)

if __name__ == "__main__":
    asyncio.run(main())
