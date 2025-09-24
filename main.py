import asyncio
from detector import fetch_whales
from notifier import log_info, log_error

async def main():
    await log_info("🚀 Whale Radar стартует...")
    try:
        await fetch_whales()
    except Exception as e:
        await log_error(f"Бот упал: {e}")

if __name__ == "__main__":
    asyncio.run(main())