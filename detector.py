import asyncio
import json
import os
import websockets
from dotenv import load_dotenv
from notifier import send_signal, log_info, log_error
from datetime import datetime

load_dotenv()

SYMBOLS = os.getenv("BINANCE_SYMBOLS", "solbusd").lower().split(",")
DEPTH = int(os.getenv("DEPTH_LEVEL", "20"))

# Пороговые значения
MIN_RELATIVE_DEPTH = float(os.getenv("MIN_RELATIVE_DEPTH", "0.3"))
MIN_ABS_VOLUME = float(os.getenv("MIN_ABS_VOLUME", "10000"))
MIN_HOLD_TIME = float(os.getenv("MIN_HOLD_TIME", "2"))
CANCEL_RATE_THRESHOLD = float(os.getenv("CANCEL_RATE_THRESHOLD", "0.6"))
MIN_CONFIDENCE = float(os.getenv("MIN_CONFIDENCE", "0.75"))

TP1_MULT = float(os.getenv("TP1_MULT", "1.5"))
TP2_MULT = float(os.getenv("TP2_MULT", "3.0"))
SL_MULT = float(os.getenv("SL_MULT", "1.0"))

async def analyze_order_book(symbol):
    ws_url = f"wss://fstream.binance.com/ws/{symbol}@depth{DEPTH}@100ms"
    try:
        async with websockets.connect(ws_url) as ws:
            await log_info(f"[{symbol.upper()}] Detector запущен.")
            async for msg in ws:
                data = json.loads(msg)
                bids = data.get("bids", [])
                asks = data.get("asks", [])

                if not bids or not asks:
                    continue

                # Видимая глубина
                total_bid_vol = sum(float(x[1]) for x in bids)
                total_ask_vol = sum(float(x[1]) for x in asks)

                # Максимальные плотности
                max_bid_price, max_bid_vol = max(((float(p), float(v)) for p, v in bids), key=lambda x: x[1])
                max_ask_price, max_ask_vol = max(((float(p), float(v)) for p, v in asks), key=lambda x: x[1])

                rel_bid_depth = max_bid_vol / total_bid_vol if total_bid_vol else 0
                rel_ask_depth = max_ask_vol / total_ask_vol if total_ask_vol else 0

                signal = None
                confidence = 0

                # Проверка на Long
                if rel_bid_depth >= MIN_RELATIVE_DEPTH and max_bid_vol >= MIN_ABS_VOLUME:
                    confidence = 0.5*rel_bid_depth + 0.5
                    if confidence >= MIN_CONFIDENCE:
                        entry = max_bid_price
                        sl = entry - (entry * SL_MULT / 100)
                        tp1 = entry + (entry * TP1_MULT / 100)
                        tp2 = entry + (entry * TP2_MULT / 100)
                        signal = ("LONG", entry, max_bid_vol, sl, tp1, tp2, confidence)

                # Проверка на Short
                elif rel_ask_depth >= MIN_RELATIVE_DEPTH and max_ask_vol >= MIN_ABS_VOLUME:
                    confidence = 0.5*rel_ask_depth + 0.5
                    if confidence >= MIN_CONFIDENCE:
                        entry = max_ask_price
                        sl = entry + (entry * SL_MULT / 100)
                        tp1 = entry - (entry * TP1_MULT / 100)
                        tp2 = entry - (entry * TP2_MULT / 100)
                        signal = ("SHORT", entry, max_ask_vol, sl, tp1, tp2, confidence)

                if signal:
                    side, price, vol, sl, tp1, tp2, conf = signal
                    await send_signal(symbol, side, price, vol, sl, tp1, tp2, conf)

    except Exception as e:
        await log_error(f"[{symbol.upper()}] Ошибка: {str(e)}")
        await asyncio.sleep(5)
        await analyze_order_book(symbol)  # перезапуск WS

async def start_detector():
    tasks = [asyncio.create_task(analyze_order_book(sym.strip())) for sym in SYMBOLS]
    await asyncio.gather(*tasks)