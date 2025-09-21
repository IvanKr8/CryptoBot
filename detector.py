import asyncio
import os
import json
import websockets
from dotenv import load_dotenv
from notifier import send_signal

load_dotenv()

SYMBOLS = os.getenv("BINANCE_SYMBOLS", "btcusdt").lower().split(",")
DEPTH = os.getenv("DEPTH_LEVEL", "20")

# Пороговые значения
MIN_RELATIVE_DEPTH = float(os.getenv("MIN_RELATIVE_DEPTH", "0.3"))
MIN_ABS_VOLUME = float(os.getenv("MIN_ABS_VOLUME", "100000"))
TP1_MULT = float(os.getenv("TP1_MULT", "1.5"))
TP2_MULT = float(os.getenv("TP2_MULT", "3.0"))
SL_MULT = float(os.getenv("SL_MULT", "1.0"))

async def detect_symbol(symbol: str):
    ws_url = f"wss://fstream.binance.com/ws/{symbol}@depth{DEPTH}@100ms"
    async with websockets.connect(ws_url) as ws:
        print(f"[Detector] Watching {symbol.upper()} at {ws_url}")
        async for msg in ws:
            data = json.loads(msg)
            bids = data.get("bids", [])
            asks = data.get("asks", [])

            if not bids or not asks:
                continue

            # Считаем видимую глубину
            total_bid_vol = sum(float(x[1]) for x in bids)
            total_ask_vol = sum(float(x[1]) for x in asks)

            # Находим максимальные плотности
            max_bid_price, max_bid_vol = max(((float(p), float(v)) for p, v in bids), key=lambda x: x[1])
            max_ask_price, max_ask_vol = max(((float(p), float(v)) for p, v in asks), key=lambda x: x[1])

            # Проверка на плотность
            rel_bid_depth = max_bid_vol / total_bid_vol if total_bid_vol else 0
            rel_ask_depth = max_ask_vol / total_ask_vol if total_ask_vol else 0

            signal = None
            if rel_bid_depth >= MIN_RELATIVE_DEPTH and max_bid_vol >= MIN_ABS_VOLUME:
                # Long сигнал
                entry = max_bid_price
                sl = entry - (entry * SL_MULT / 100)  # стоп как % от цены
                tp1 = entry + (entry * TP1_MULT / 100)
                tp2 = entry + (entry * TP2_MULT / 100)
                signal = ("LONG", entry, max_bid_vol, sl, tp1, tp2, rel_bid_depth)

            elif rel_ask_depth >= MIN_RELATIVE_DEPTH and max_ask_vol >= MIN_ABS_VOLUME:
                # Short сигнал
                entry = max_ask_price
                sl = entry + (entry * SL_MULT / 100)
                tp1 = entry - (entry * TP1_MULT / 100)
                tp2 = entry - (entry * TP2_MULT / 100)
                signal = ("SHORT", entry, max_ask_vol, sl, tp1, tp2, rel_ask_depth)

            if signal:
                side, price, vol, sl, tp1, tp2, conf = signal
                await send_signal(symbol, side, price, vol, sl, tp1, tp2, conf)

async def start_detector():
    tasks = [asyncio.create_task(detect_symbol(sym.strip())) for sym in SYMBOLS]
    await asyncio.gather(*tasks)