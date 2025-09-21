import os
from dotenv import load_dotenv
from telegram import Bot

load_dotenv()
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

bot = Bot(token=TELEGRAM_TOKEN)

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
    await bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=msg)