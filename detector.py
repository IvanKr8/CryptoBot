# detector.py
import os
import json
import asyncio
import websockets
from dotenv import load_dotenv
from notifier import log_info

load_dotenv()

BINANCE_SYMBOLS = os.getenv("BINANCE_SYMBOLS", "vetusdt,trbusdt,adausdt").split(",")
DEPTH_LEVEL = int(os.getenv("DEPTH_LEVEL", 10))

# Пороговые значения
MIN_RELATIVE_DEPTH = float(os.getenv("MIN_RELATIVE_DEPTH", 0.3))
MIN_ABS_VOLUME = float(os.getenv("MIN_ABS_VOLUME", 10000))
MIN_HOLD_TIME = float(os.getenv("MIN_HOLD_TIME", 2))
CANCEL_RATE_THRESHOLD = float(os.getenv("CANCEL_RATE_THRESHOLD", 0.6))
MIN_CONFIDENCE = float(os.getenv("MIN_CONFIDENCE", 0.75))


async def whales_detector():
    streams = "/".join([f"{s}@depth{DEPTH_LEVEL}" for s in BINANCE_SYMBOLS])
    url = f"wss://fstream.binance.com/stream?streams={streams}"

    await log_info("✅ Detector запущен и подключается к Binance...")

    first_run_results = []  # для хранения данных первой итерации

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

                        # Обработка первой итерации только для первых 2 токенов
                        if symbol.lower() in BINANCE_SYMBOLS[:2]:
                            for b in bids:
                                price, volume = float(b[0]), float(b[1])
                                total_bid_volume = sum(float(bi[1]) for bi in bids)
                                rel_depth = volume / total_bid_volume if total_bid_volume > 0 else 0
                                if volume >= MIN_ABS_VOLUME and rel_depth >= MIN_RELATIVE_DEPTH:
                                    confidence = rel_depth
                                    if confidence >= MIN_CONFIDENCE:
                                        first_run_results.append(
                                            f"🚨 LONG {symbol} | Price: {price} | Vol: {volume} | RelDepth: {rel_depth:.2f} | Conf: {confidence:.2f}"
                                        )
                            for a in asks:
                                price, volume = float(a[0]), float(a[1])
                                total_ask_volume = sum(float(ai[1]) for ai in asks)
                                rel_depth = volume / total_ask_volume if total_ask_volume > 0 else 0
                                if volume >= MIN_ABS_VOLUME and rel_depth >= MIN_RELATIVE_DEPTH:
                                    confidence = rel_depth
                                    if confidence >= MIN_CONFIDENCE:
                                        first_run_results.append(
                                            f"🚨 SHORT {symbol} | Price: {price} | Vol: {volume} | RelDepth: {rel_depth:.2f} | Conf: {confidence:.2f}"
                                        )

                            # После обработки первых токенов отправляем один итоговый лог
                            if first_run_results:
                                await log_info("📊 Итоги первой проверки:\n" + "\n".join(first_run_results))
                                first_run_results = []  # очищаем, чтобы не слать повторно

                        # Далее обычная логика для всех остальных токенов (или можно пока оставить pass)
                        # ...

                        await asyncio.sleep(0.1)

                    except Exception as e:
                        await log_info(f"❌ Ошибка при обработке данных: {e}")
                        await asyncio.sleep(1)

        except (websockets.exceptions.ConnectionClosedError,
                websockets.exceptions.ConnectionClosedOK,
                asyncio.TimeoutError) as e:
            await log_info(f"⚠️ Соединение закрыто или таймаут: {e}. Переподключаемся...")
            await asyncio.sleep(5)