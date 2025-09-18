import asyncio
import json
import websockets
from telegram import Bot
from datetime import datetime

# --- Настройки ---
BOT_TOKEN = "8275504974:AAEJblNngby0n-XEEUNn0nVe4y_BxAVEEsw"  # <-- сюда вставь токен бота
CHAT_ID = 921726824             # <-- твой ID
BINANCE_WS_URL = "wss://stream.binance.com:9443/ws/!bookTicker"
CHECK_LEVELS = 10               # уровни для visible_depth
CONFIDENCE_THRESHOLD = 0.75

# --- Telegram бот ---
bot = Bot(token=BOT_TOKEN)

# --- Данные по токенам ---
tokens = [
    "SOLUSDT", "ETHUSDT", "BNBUSDT", "ADAUSDT", "XRPUSDT",
    "DOTUSDT", "MATICUSDT", "LTCUSDT", "AVAXUSDT", "LINKUSDT",
]

# --- Состояние ордеров ---
order_book = {}  # symbol -> {price: {volume, timestamp, cancel_count}}
ALPHA = 0.1  # скользящее среднее
LARGE_ORDER_MULTIPLIER = 5
last_notify_time = 0
NOT_FOUND_TIMEOUT = 10

# --- Функции ---
def update_level(symbol, price, volume):
    now = datetime.utcnow().timestamp()
    if symbol not in order_book:
        order_book[symbol] = {}
    if price not in order_book[symbol]:
        order_book[symbol][price] = {"volume": volume, "timestamp": now, "cancel_count": 0}
    else:
        order_book[symbol][price]["volume"] = (1-ALPHA)*order_book[symbol][price]["volume"] + ALPHA*volume
        order_book[symbol][price]["timestamp"] = now

def compute_metrics(symbol, price):
    level = order_book[symbol][price]
    now = datetime.utcnow().timestamp()
    hold_time = now - level["timestamp"]
    volume_at_level = level["volume"]
    visible_depth = sum([v["volume"] for v in order_book[symbol].values()])
    relative_depth = volume_at_level / visible_depth if visible_depth > 0 else 0
    cancel_rate = level["cancel_count"] / (hold_time+0.001)
    return {
        "volume": volume_at_level,
        "hold_time": hold_time,
        "relative_depth": relative_depth,
        "cancel_rate": cancel_rate
    }

def confidence_score(metrics):
    w1, w2, w3 = 0.35, 0.25, 0.2
    score = (metrics["relative_depth"]*w1 +
             min(metrics["hold_time"]/60,1)*w2 +  # нормируем hold_time до 60s
             (1 - min(metrics["cancel_rate"],1))*w3)
    return score

async def notify_large_order(symbol, side, price, metrics):
    msg = (f"Большой ордер!\nТокен: {symbol}\nСторона: {side}\n"
           f"Цена: {price}\nОбъем: {metrics['volume']:.3f}\n"
           f"Время висения: {metrics['hold_time']:.1f}s\n"
           f"Relative_depth: {metrics['relative_depth']:.2f}\n"
           f"Cancel_rate: {metrics['cancel_rate']:.2f}")
    await bot.send_message(chat_id=CHAT_ID, text=msg)

async def notify_not_found():
    msg = "Пока крупных ордеров не найдено. Текущие средние объемы:\n"
    for symbol in tokens:
        total_volume = sum([v["volume"] for v in order_book.get(symbol, {}).values()])
        msg += f"{symbol}: {total_volume:.4f}\n"
    await bot.send_message(chat_id=CHAT_ID, text=msg)

# --- Основной цикл ---
async def main():
    global last_notify_time
    async with websockets.connect(BINANCE_WS_URL) as ws:
        while True:
            try:
                msg = await asyncio.wait_for(ws.recv(), timeout=NOT_FOUND_TIMEOUT)
                data = json.loads(msg)
                symbol = data["s"]
                if symbol not in tokens:
                    continue

                bid_price = float(data["b"])
                ask_price = float(data["a"])
                bid_size = float(data["B"])
                ask_size = float(data["A"])

                # обновляем уровни
                update_level(symbol, bid_price, bid_size)
                update_level(symbol, ask_price, ask_size)

                # проверяем метрики
                bid_metrics = compute_metrics(symbol, bid_price)
                ask_metrics = compute_metrics(symbol, ask_price)

                if confidence_score(bid_metrics) >= CONFIDENCE_THRESHOLD:
                    await notify_large_order(symbol, "BUY", bid_price, bid_metrics)
                    last_notify_time = asyncio.get_event_loop().time()
                elif confidence_score(ask_metrics) >= CONFIDENCE_THRESHOLD:
                    await notify_large_order(symbol, "SELL", ask_price, ask_metrics)
                    last_notify_time = asyncio.get_event_loop().time()

            except asyncio.TimeoutError:
                now = asyncio.get_event_loop().time()
                if now - last_notify_time >= NOT_FOUND_TIMEOUT:
                    await notify_not_found()
                    last_notify_time = now

if __name__ == "__main__":
    asyncio.run(main())