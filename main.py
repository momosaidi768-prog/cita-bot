import asyncio

print("🔥 BOT STARTING...")

async def main():

    print("🤖 BOT RUNNING")

    while True:
        try:
            print("🔁 alive")
            await asyncio.sleep(10)

        except Exception as e:
            print("ERROR:", e)

if __name__ == "__main__":
    asyncio.run(main())
