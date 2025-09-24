from dotenv import load_dotenv
import os
import websockets
import asyncio

load_dotenv()

BINANCE_SYMBOLS = os.getenv("BINANCE_SYMBOLS", "vetusdt,trbusdt").split(",")
DEPTH_LEVEL = os.getenv("DEPTH_LEVEL", 10)

async def whales_detector():
   streams = "/".join([f"{s}@depth20" for s in BINANCE_SYMBOLS])
   url = f"wss://fstream.binance.com/stream?streams={streams}"
   
   async with websockets.connect(url) as ws:
        print("✅ Подключено. Жду данные ордербуков...")
        async for message in ws:
            data = json.loads(message)
            symbol = data["stream"].split("@")[0]
            orderbook = data["data"]

            bids = orderbook["bids"]
            asks = orderbook["asks"]

            print(f"\n📈 {symbol.upper()} — обновление стакана:")
            print(f"   🔵 Лучшая покупка: {bids[0]}")
            print(f"   🔴 Лучшая продажа: {asks[0]}")

            await asyncio.sleep(0.1)

    