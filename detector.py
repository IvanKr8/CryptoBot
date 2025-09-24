# detector.py
import os
import json
import asyncio
import websockets
from dotenv import load_dotenv
from notifier import log_info

load_dotenv()

BINANCE_SYMBOLS = os.getenv("BINANCE_SYMBOLS", "vetusdt,trbusdt").split(",")
DEPTH_LEVEL = int(os.getenv("DEPTH_LEVEL", 10))

# Пороговые значения
MIN_RELATIVE_DEPTH = float(os.getenv("MIN_RELATIVE_DEPTH", 0.3))
MIN_ABS_VOLUME = float(os.getenv("MIN_ABS_VOLUME", 10000))
MIN_HOLD_TIME = float(os.getenv("MIN_HOLD_TIME", 2))
CANCEL_RATE_THRESHOLD = float(os.getenv("CANCEL_RATE_THRESHOLD", 0.6))

# Confidence
MIN_CONFIDENCE = float(os.getenv("MIN_CONFIDENCE", 0.75))


# Для хранения прошлых состояний уровней, чтобы считать hold_time и cancel_rate
level_cache = {}  # {symbol: {price_level: {"volume": float, "hold_time": float, "last_update": timestamp}}}


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

                        # Считаем видимую глубину
                        total_bid_volume = sum(float(b[1]) for b in bids)
                        total_ask_volume = sum(float(a[1]) for a in asks)

                        # Анализируем каждый уровень на bids
                        for b in bids:
                            price, volume = float(b[0]), float(b[1])
                            rel_depth = volume / total_bid_volume if total_bid_volume > 0 else 0

                            if volume < MIN_ABS_VOLUME or rel_depth < MIN_RELATIVE_DEPTH:
                                continue  # фильтруем мелкие и слабые уровни

                            # Здесь можно добавить hold_time/cancel_rate если хранить прошлое
                            confidence = rel_depth  # простая метрика пока

                            if confidence >= MIN_CONFIDENCE:
                                text = (
                                    f"🚨 Сигнал LONG для {symbol}\n"
                                    f"Цена уровня: {price}\n"
                                    f"Объем: {volume}\n"
                                    f"Relative Depth: {rel_depth:.2f}\n"
                                    f"Confidence: {confidence:.2f}"
                                )
                                await log_info(text)

                        # Аналогично анализируем asks для SHORT
                        for a in asks:
                            price, volume = float(a[0]), float(a[1])
                            rel_depth = volume / total_ask_volume if total_ask_volume > 0 else 0

                            if volume < MIN_ABS_VOLUME or rel_depth < MIN_RELATIVE_DEPTH:
                                continue

                            confidence = rel_depth
                            if confidence >= MIN_CONFIDENCE:
                                text = (
                                    f"🚨 Сигнал SHORT для {symbol}\n"
                                    f"Цена уровня: {price}\n"
                                    f"Объем: {volume}\n"
                                    f"Relative Depth: {rel_depth:.2f}\n"
                                    f"Confidence: {confidence:.2f}"
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