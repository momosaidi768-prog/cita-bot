async def worker():

    global running

    try:

        async with async_playwright() as p:

            print("🚀 STARTING BROWSER...")

            browser = await p.chromium.launch(
                headless=True,
                timeout=120000,
                args=[
                    "--no-sandbox",
                    "--disable-setuid-sandbox",
                    "--disable-dev-shm-usage",
                    "--disable-gpu",
                    "--disable-blink-features=AutomationControlled"
                ]
            )

            print("✅ BROWSER STARTED")

            page = await browser.new_page()

            await tg.send("🤖 Bot started successfully")

            while running:

                users = get_users()

                for user in users:

                    name, nie, phone, email, cities = user

                    city_list = [c.strip() for c in cities.split(",")]

                    for city in city_list:

                        result = await check(page, city)

                        if result:

                            try:

                                await page.screenshot(
                                    path="shot.png",
                                    full_page=True
                                )

                                form = aiohttp.FormData()

                                form.add_field("chat_id", str(ADMIN_ID))

                                form.add_field(
                                    "caption",
                                    f"""
🔥 APPOINTMENT FOUND

👤 {name}
📄 {nie}
📍 {city}
🔗 {result}

⚠ Confirm manually
"""
                                )

                                form.add_field(
                                    "photo",
                                    open("shot.png", "rb"),
                                    filename="shot.png",
                                    content_type="image/png"
                                )

                                await tg.session.post(
                                    f"{TG_URL}/sendPhoto",
                                    data=form
                                )

                                print("📸 Screenshot sent")

                            except Exception as e:

                                print("PHOTO ERROR:", e)

                                await tg.send(f"🔥 FOUND\n{result}")

                            await asyncio.sleep(60)

                        await asyncio.sleep(2)

    except Exception as e:

        print("WORKER ERROR:", e)

        await tg.send(f"❌ WORKER ERROR:\n{e}")
