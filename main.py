import asyncio
from detector import whales_detector
from notifier import log_info, log_error

async def main():
    await log_info("🚀 Detector бот стартует...")
    try:
        await whales_detector()
    except Exception as e:
        await log_error(f"Бот упал с ошибкой: {str(e)}")

if __name__ == "__main__":
    asyncio.run(main())