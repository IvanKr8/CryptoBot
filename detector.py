from dotenv import load_dotenv
import os

load_dotenv()

BINANCE_SYMBOLS = os.getenv("BINANCE_SYMBOLS", "vetusdt,trbusdt").split(",")

async def whales_detector():
    