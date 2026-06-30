"""
scheduler.py — Checks Forex Factory every 5 minutes for events happening
within the next 15 minutes, and posts a real-time alert when found.

This is the engine that makes the bot feel "live" — same approach used
by popular forex news alert bots/channels.
"""

import asyncio
import logging
from dotenv import load_dotenv
load_dotenv()

from bot import run_check

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

CHECK_INTERVAL_SECONDS = 300   # 5 minutes


async def scheduler():
    log.info("📡 Real-time news scheduler started. Checking every 5 minutes...")
    while True:
        try:
            await run_check()
        except Exception as e:
            log.error("Check cycle failed: %s", e)
        await asyncio.sleep(CHECK_INTERVAL_SECONDS)


if __name__ == "__main__":
    asyncio.run(scheduler())
