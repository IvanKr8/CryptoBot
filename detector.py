import os
import json
import asyncio
import websockets
from dotenv import load_dotenv
from notifier import log_info, send_signal

load_dotenv()

BINANCE_SYMBOLS = os.getenv("BINANCE_SYMBOLS", "vetusdt,trbusdt").split(",")
DEPTH_LEVEL = int(os.getenv("DEPTH_LEVEL", 20))
MIN_RELATIVE_DEPTH = float(os.getenv("MIN_RELATIVE_DEPTH", 0.3))
MIN_ABS_VOLUME = float(os.getenv("MIN_ABS_VOLUME", 100000))
MIN_HOLD_TIME = float(os.getenv("MIN_HOLD_TIME", 2))
CANCEL_RATE_THRESHOLD = float(os.getenv("CANCEL_RATE_THRESHOLD", 0.6))
MIN_CONFIDENCE = float(os.getenv("MIN_CONFIDENCE", 0.75))

async def analyze_orderbook(symbol, bids, asks):
    total_bid = sum(float(b[1]) for b in bids)
    total_ask = sum(float(a[1]) for a in asks)

    for b in bids:
        price, volume = float(b[0]), float(b[1])
        rd = volume / total_bid if total_bid > 0 else 0
        confidence = rd
        if volume >= MIN_ABS_VOLUME and rd >= MIN_RELATIVE_DEPTH and confidence >= MIN_CONFIDENCE:
            await send_signal(symbol, "LONG", price, volume, rd, confidence)

    for a in asks:
        price, volume = float(a[0]), float(a[1])
        rd = volume / total_ask if total_ask > 0 else 0
        confidence = rd
        if volume >= MIN_ABS_VOLUME and rd >= MIN_RELATIVE_DEPTH and confidence >= MIN_CONFIDENCE:
            await send_signal(symbol, "SHORT", price, volume, rd, confidence)

async def whales_detector():
    streams = "/".join([f"{s}@depth{DEPTH_LEVEL}" for s in BINANCE_SYMBOLS])
    url = f"wss://fstream.binance.com/stream?streams={streams}"
    await log_info("✅ Detector запущен и подключается к Binance...")

    while True:
        try:
            async with websockets.connect(url, ping_interval=20, ping_timeout=10) as ws:
                await log_info("📡 Подключение к Binance установлено. Жду обновления стаканов...")
                async for message in ws:
                    try:
                        data = json.loads(message)
                        symbol = data["stream"].split("@")[0].upper()
                        orderbook = data["data"]
                        bids = orderbook.get("b", [])[:DEPTH_LEVEL]
                        asks = orderbook.get("a", [])[:DEPTH_LEVEL]
                        await analyze_orderbook(symbol, bids, asks)
                        await asyncio.sleep(0.05)
                    except Exception as e:
                        await log_info(f"❌ Ошибка обработки: {e}")
                        await asyncio.sleep(1)
        except (websockets.exceptions.ConnectionClosedError, asyncio.TimeoutError) as e:
            await log_info(f"⚠️ Соединение закрыто/таймаут: {e}. Переподключаемся...")
            await asyncio.sleep(5)