import asyncio
from detector import start_detector

async def main():
    await start_detector()

if __name__ == "__main__":
    asyncio.run(main())