import asyncio
import websockets
import json
from notifier import log_info
from dotenv import load_dotenv
import os

load_dotenv()

BINANCE_SYMBOLS = os.getenv("BINANCE_SYMBOLS", "vetusdt,trbusdt").split(",")
DEPTH_LEVEL = os.getenv("DEPTH_LEVEL", 10)

async def whales_detector():
    await log_info(BINANCE_SYMBOLS")
    streams = "/".join([f"{s}@depth20" for s in BINANCE_SYMBOLS])
    url = f"wss://fstream.binance.com/stream?streams={streams}"

    await log_info("✅ Detector запущен и подключается к Binance...")

    while True:  # бесконечный цикл переподключений
        try:
            async with websockets.connect(url, ping_interval=20, ping_timeout=10) as ws:
                await log_info("📡 Подключение к Binance установлено. Жду обновления стаканов...")
                async for message in ws:
                    try:
                        data = json.loads(message)
                        symbol = data["stream"].split("@")[0].upper()
                        orderbook = data["data"]

                        bids = orderbook.get("b", [])
                        asks = orderbook.get("a", [])

                        if bids and asks:
                            text = (
                                f"📈 {symbol} — обновление стакана\n"
                                f"🔵 Лучшая покупка: {bids[0]}\n"
                                f"🔴 Лучшая продажа: {asks[0]}"
                            )
                            await log_info(text)

                        await asyncio.sleep(0.1)

                    except Exception as e:
                        await log_info(f"❌ Ошибка при обработке данных: {e}")
                        await asyncio.sleep(1)

        except (websockets.exceptions.ConnectionClosedError,
                websockets.exceptions.ConnectionClosedOK,
                asyncio.TimeoutError) as e:
            await log_info(f"⚠️ Соединение закрыто или таймаут: {e}. Переподключаемся...")
            await asyncio.sleep(5)