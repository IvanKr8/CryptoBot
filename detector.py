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
MIN_USD_VOLUME = float(os.getenv("MIN_USD_VOLUME", 500000))
MIN_HOLD_TIME = float(os.getenv("MIN_HOLD_TIME", 2))
CANCEL_RATE_THRESHOLD = float(os.getenv("CANCEL_RATE_THRESHOLD", 0.6))
MIN_CONFIDENCE = float(os.getenv("MIN_CONFIDENCE", 0.8))

level_cache = {}

async def fetch_whales():
    streams = "/".join([f"{s}@depth{DEPTH_LEVEL}" for s in BINANCE_SYMBOLS])
    url = f"wss://fstream.binance.com/stream?streams={streams}"

    while True:
        try:
            async with websockets.connect(url, ping_interval=20, ping_timeout=10) as ws:
                await log_info("✅ Подключено к Binance")
                async for message in ws:
                    try:
                        data = json.loads(message)
                        symbol = data["stream"].split("@")[0].upper()
                        orderbook = data["data"]
                        bids = orderbook.get("b", [])[:DEPTH_LEVEL]
                        asks = orderbook.get("a", [])[:DEPTH_LEVEL]

                        total_bid_usd = sum(float(b[1])*float(b[0]) for b in bids)
                        total_ask_usd = sum(float(a[1])*float(a[0]) for a in asks)

                        for b in bids:
                            price, volume = float(b[0]), float(b[1])
                            volume_usd = price*volume
                            rel_depth = volume_usd/total_bid_usd if total_bid_usd>0 else 0
                            confidence = rel_depth
                            if volume_usd >= MIN_USD_VOLUME and rel_depth >= MIN_RELATIVE_DEPTH and confidence>=MIN_CONFIDENCE:
                                await send_signal(symbol, "LONG", price, volume_usd, rel_depth, confidence)

                        for a in asks:
                            price, volume = float(a[0]), float(a[1])
                            volume_usd = price*volume
                            rel_depth = volume_usd/total_ask_usd if total_ask_usd>0 else 0
                            confidence = rel_depth
                            if volume_usd >= MIN_USD_VOLUME and rel_depth >= MIN_RELATIVE_DEPTH and confidence>=MIN_CONFIDENCE:
                                await send_signal(symbol, "SHORT", price, volume_usd, rel_depth, confidence)

                        await asyncio.sleep(0.1)

                    except Exception as e:
                        await log_info(f"❌ Ошибка обработки данных: {e}")
                        await asyncio.sleep(1)

        except (websockets.exceptions.ConnectionClosedError,
                websockets.exceptions.ConnectionClosedOK,
                asyncio.TimeoutError) as e:
            await log_info(f"⚠️ Соединение закрыто: {e}. Переподключаемся...")
            await asyncio.sleep(5)