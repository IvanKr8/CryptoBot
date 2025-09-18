import asyncio
import json
import websockets
from telegram import Bot

BOT_TOKEN = "8275504974:AAEJblNngby0n-XEEUNn0nVe4y_BxAVEEsw"
CHAT_ID = 921726824  # твой ID
HYPERLIQUID_WS_URL = "wss://api.hyperliquid.com/ws"  # пример

bot = Bot(token=BOT_TOKEN)

# Скользящее среднее ордеров для каждого токена
token_avg_order_size = {}
ALPHA = 0.1  # коэффициент для скользящего среднего
LARGE_ORDER_MULTIPLIER = 5  # ордер > 5x среднего считается крупным
NOT_FOUND_TIMEOUT = 10  # секунд

last_large_order_time = 0
observed_tokens = set()

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
    msg = f"Большой ордер!\nТокен: {symbol}\nСторона: {side}\nОбъем: {size}\nЦена: {price}"
    await bot.send_message(chat_id=CHAT_ID, text=msg)

async def notify_not_found():
    tokens_list = ", ".join(observed_tokens) if observed_tokens else "Наблюдаемых токенов пока нет"
    msg = f"Пока крупных ордеров не найдено.\nТокены, которые проверялись: {tokens_list}"
    await bot.send_message(chat_id=CHAT_ID, text=msg)

async def main():
    global last_large_order_time
    async with websockets.connect(HYPERLIQUID_WS_URL) as ws:
        while True:
            try:
                msg = await asyncio.wait_for(ws.recv(), timeout=NOT_FOUND_TIMEOUT)
                data = json.loads(msg)

                # Печатаем все полученные данные
                print(json.dumps(data, indent=2, ensure_ascii=False))

                # Пример структуры, нужно подставить реально по HyperLiquid:
                symbol = data.get("coin") or data.get("symbol")
                if not symbol:
                    continue

                bid_price = float(data.get("bid_price", 0))
                ask_price = float(data.get("ask_price", 0))
                bid_size = float(data.get("bid_size", 0))
                ask_size = float(data.get("ask_size", 0))

                observed_tokens.add(symbol)

                # обновляем средние значения
                update_avg_order(symbol, bid_size)
                update_avg_order(symbol, ask_size)

                # проверяем крупные ордера
                if is_large_order(symbol, bid_size):
                    await notify_large_order(symbol, "BUY", bid_size, bid_price)
                elif is_large_order(symbol, ask_size):
                    await notify_large_order(symbol, "SELL", ask_size, ask_price)

            except asyncio.TimeoutError:
                if asyncio.get_event_loop().time() - last_large_order_time >= NOT_FOUND_TIMEOUT:
                    await notify_not_found()
                    last_large_order_time = asyncio.get_event_loop().time()
            except Exception as e:
                print(f"Ошибка: {e}")
                await asyncio.sleep(1)

if __name__ == "__main__":
    asyncio.run(main())