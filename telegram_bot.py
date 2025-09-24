from telegram.ext import ApplicationBuilder, CommandHandler
import os
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_LOG_TOKEN = os.getenv("TELEGRAM_LOG_TOKEN")

async def start_signal(update, context):
    await update.message.reply_text("Я работаю (Detector Bot).")

async def start_log(update, context):
    await update.message.reply_text("Я работаю (Log Bot).")

app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
app.add_handler(CommandHandler("start", start_signal))
app.run_polling()