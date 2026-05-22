import os
import aiohttp
import asyncio

TOKEN = os.getenv("8202293986:AAHL6nkd54h-D4_CTid6P9IQYcjj3nYQ9n8")
ADMIN_ID = int(os.getenv("6675176280"))

TG_URL = f"https://api.telegram.org/bot{TOKEN}/sendMessage"

async def send(msg):
    async with aiohttp.ClientSession() as s:
        await s.post(TG_URL, data={
            "chat_id": ADMIN_ID,
            "text": msg
        })

async def main():

    await send("🤖 Bot started successfully!")

    offset = 0  # مهم جداً

    while True:
        try:
            async with aiohttp.ClientSession() as s:
                url = f"https://api.telegram.org/bot{TOKEN}/getUpdates"
                async with s.get(url, params={"offset": offset}) as r:
                    data = await r.json()

            for upd in data.get("result", []):
                offset = upd["update_id"] + 1  # يمنع التكرار

                if "message" in upd:
                    text = upd["message"]["text"]

                    # تجاهل رسائل النظام
                    if text.startswith("/"):
                        await send("✅ Command received")
                    else:
                        await send(f"📩 Echo: {text}")

        except Exception as e:
            print("error:", e)

        await asyncio.sleep(2)

if __name__ == "__main__":
    asyncio.run(main())
