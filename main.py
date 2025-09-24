import asyncio
from detector import whales_detector
from notifier import log_info

async def main():
    await log_info("🚀 Detector бот стартует...")
    await whales_detector()

if __name__ == "__main__":
    asyncio.run(main())