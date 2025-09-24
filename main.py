import asyncio
from telegram.ext import ApplicationBuilder, CommandHandler
from detector import whales_detector
from notifier import log_info
import os
from dotenv import load_dotenv

load_dotenv()
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")

async def start_signal(update, context):
    await update.message.reply_text("Я работаю (Detector Bot).")

async def main():
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start_signal))
    await app.initialize()
    await app.start()
    
    # Запуск бота по WebSocket
    asyncio.create_task(whales_detector())

    # Держим приложение живым
    await app.updater.start_polling()
    await app.updater.idle()

if __name__ == "__main__":
    asyncio.run(main())