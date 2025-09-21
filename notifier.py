import os
from dotenv import load_dotenv
from telegram import Bot
import asyncio

load_dotenv()

# Сигналы
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
bot_signals = Bot(token=TELEGRAM_TOKEN)

# Логи
TELEGRAM_LOG_TOKEN = os.getenv("TELEGRAM_LOG_TOKEN")
TELEGRAM_LOG_CHAT_ID = os.getenv("TELEGRAM_LOG_CHAT_ID")
bot_logs = Bot(token=TELEGRAM_LOG_TOKEN)

async def send_signal(symbol, side, price_level, volume, sl, tp1, tp2, confidence):
    msg = (
        f"🚨 Сигнал по {symbol.upper()}\n"
        f"Side: {side}\n"
        f"Цена уровня: {price_level}\n"
        f"Объем: {volume}\n"
        f"SL: {sl}\n"
        f"TP1: {tp1}\n"
        f"TP2: {tp2}\n"
        f"Уверенность: {confidence:.2f}"
    )
    await bot_signals.send_message(chat_id=TELEGRAM_CHAT_ID, text=msg)

async def log_info(message):
    await bot_logs.send_message(chat_id=TELEGRAM_LOG_CHAT_ID, text=f"ℹ️ {message}")

async def log_error(message):
    await bot_logs.send_message(chat_id=TELEGRAM_LOG_CHAT_ID, text=f"❌ {message}")