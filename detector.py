from dotenv import load_dotenv
import os
import websockets
import asyncio

load_dotenv()

BINANCE_SYMBOLS = os.getenv("BINANCE_SYMBOLS", "vetusdt,trbusdt").split(",")
DEPTH_LEVEL = os.getenv("DEPTH_LEVEL", 10)

async def whales_detector():
    streams = "/".join([f"{s}@depth{DEPTH_LEVEL}" for s in BINANCE_SYMBOLS])
    url = f"wss://fstream.binance.com/stream?streams={streams}"

    await log_info("✅ Detector запущен и подключается к Binance...")

    async with websockets.connect(url) as ws:
        await log_info("📡 Подключение к Binance установлено. Жду обновления стаканов...")
        async for message in ws:
            try:
                data = json.loads(message)
                symbol = data["stream"].split("@")[0].upper()
                orderbook = data["data"]

                bids = orderbook["bids"]
                asks = orderbook["asks"]

                text = (
                    f"📈 Обновление стакана для {symbol}\n"
                    f"🔵 Лучшая покупка: {bids[0]}\n"
                    f"🔴 Лучшая продажа: {asks[0]}"
                )

                await log_info(text)
                await asyncio.sleep(0.2)  # чуть замедляем, чтобы Telegram не душился

            except Exception as e:
                await log_info(f"❌ Ошибка при обработке данных: {e}")
                await asyncio.sleep(1)

    