import asyncio
from detector import fetch_whales, send_periodic_log
from notifier import log_info, log_error

async def main():
    await log_info("🚀 Whale Radar стартует...")
    try:
        task1 = asyncio.create_task(fetch_whales())
        task2 = asyncio.create_task(send_periodic_log())
        await asyncio.gather(task1, task2)
    except Exception as e:
        await log_error(f"Бот упал: {e}")

if __name__ == "__main__":
    asyncio.run(main())