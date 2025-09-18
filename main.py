import asyncio
import json
import websockets
from telegram import Bot

BOT_TOKEN = "8275504974:AAEJblNngby0n-XEEUNn0nVe4y_BxAVEEsw"
CHAT_ID = 921726824  # твой ID
HYPERLIQUID_WS_URL = "wss://api.hyperliquid.xyz/ws"

bot = Bot(token=BOT_TOKEN)

# Скользящее среднее ордеров для каждого токена
token_avg_order_size = {}
ALPHA = 0.1  # коэффициент для скользящего среднего
LARGE_ORDER_MULTIPLIER = 5  # ордер > 5x среднего считается крупным
NOT_FOUND_TIMEOUT = 10  # секунд

last_large_order_time = 0

def update_avg_order(symbol, size):
    if symbol not in token_avg_order_size:
        token_avg_order_size[symbol] = size
    else:
        token_avg_order_size[symbol] = (1 - ALPHA) * token_avg_order_size[symbol] + ALPHA * size

def is_large_order(symbol, size):
    avg = token_avg_order_size.get(symbol, size)
    return size >= avg * LARGE_ORDER_MULTIPLIER

async def notify_large_order(symbol, side, size, price):
    global last_large_order_time
    last_large_order_time = asyncio.get_event_loop().time()
    msg = (
        f"🚨 Большой ордер!\n"
        f"Токен: {symbol}\n"
        f"Сторона: {side}\n"
        f"Объем: {size}\n"
        f"Цена: {price}"
    )
    await bot.send_message(chat_id=CHAT_ID, text=msg)

async def notify_not_found():
    if not token_avg_order_size:
        msg = "Пока крупных ордеров не найдено. Наблюдаемых токенов пока нет."
    else:
        lines = ["Пока крупных ордеров не найдено.", "Наблюдаемые токены:"]
        for symbol, avg_size in token_avg_order_size.items():
            lines.append(f"{symbol}: средний объем ≈ {avg_size:.4f}")
        msg = "\n".join(lines)
    await bot.send_message(chat_id=CHAT_ID, text=msg)

async def main():
    global last_large_order_time
    async with websockets.connect(HYPERLIQUID_WS_URL) as ws:
        # Подписка на данные стакана для всех токенов
        await ws.send(json.dumps({
            "method": "subscribe",
            "subscription": {
                "type": "l2Book",
                "coin": "SOL"  # Пример для SOL, добавь другие токены по мере необходимости
            }
        }))
        while True:
            try:
                msg = await asyncio.wait_for(ws.recv(), timeout=1)  # таймаут 1 сек
                data = json.loads(msg)

                symbol = data["coin"]
                bid_price = float(data["levels"][0][0]["px"])
                ask_price = float(data["levels"][1][0]["px"])
                bid_size = float(data["levels"][0][0]["sz"])
                ask_size = float(data["levels"][1][0]["sz"])

                # обновляем средние значения
                update_avg_order(symbol, bid_size)
                update_avg_order(symbol, ask_size)

                # проверяем крупные ордера
                if is_large_order(symbol, bid_size):
                    await notify_large_order(symbol, "BUY", bid_size, bid_price)
                elif is_large_order(symbol, ask_size):
                    await notify_large_order(symbol, "SELL", ask_size, ask_price)

            except asyncio.TimeoutError:
                pass  # просто ждем следующего сообщения

            # проверка таймера уведомления о пустых ордерах
            now = asyncio.get_event_loop().time()
            if now - last_large_order_time >= NOT_FOUND_TIMEOUT:
                await notify_not_found()
                last_large_order_time = now

if __name__ == "__main__":
    asyncio.run(main())