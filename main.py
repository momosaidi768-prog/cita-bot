import os
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# قراءة التوكن من Railway Variables
TOKEN = os.getenv("BOT_TOKEN")

# فحص التوكن
print("TOKEN:", repr(TOKEN))

if not TOKEN:
    raise ValueError("BOT_TOKEN غير موجود في Railway Variables!")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("البوت خدام ✅")

# إنشاء البوت
app = ApplicationBuilder().token(TOKEN.strip()).build()

# الأوامر
app.add_handler(CommandHandler("start", start))

print("Bot started...")

# تشغيل البوت
app.run_polling()
