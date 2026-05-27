const { chromium } = require('playwright');
const TelegramBot = require('node-telegram-bot-api');

const bot = new TelegramBot(process.env.BOT_TOKEN);
const CHAT_ID = process.env.CHAT_ID;

async function checkPage() {
  const browser = await chromium.launch({ headless: true });

  try {
    const page = await browser.newPage();

    await page.goto('https://example.com', {
      waitUntil: 'networkidle'
    });

    const text = await page.locator('body').innerText();

    // إرسال أول 3000 حرف لتجنب حد تيليغرام
    await bot.sendMessage(
      CHAT_ID,
      `📄 تحديث الصفحة:\n\n${text.slice(0, 3000)}`
    );

  } catch (err) {
    await bot.sendMessage(
      CHAT_ID,
      `❌ خطأ:\n${err.message}`
    );
  } finally {
    await browser.close();
  }
}

setInterval(checkPage, 5 * 60 * 1000);

// تشغيل أول مرة مباشرة
checkPage();
