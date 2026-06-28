"""
scheduler.py — Runs the FX Elite Desk news bot daily.

Schedule (UTC):
  07:00  Morning news digest
  13:00  Midday US session preview (optional second run)

Run this file once and it keeps posting forever:
    python scheduler.py
"""

import asyncio
import logging
from datetime import datetime, timezone
from dotenv import load_dotenv
load_dotenv()

from bot import run   # import main bot function

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

# Times to post (24-hr UTC)
POST_HOURS = [7, 13]   # 7 AM and 1 PM UTC


async def scheduler():
    log.info("📅 Scheduler started. Will post at hours: %s UTC", POST_HOURS)
    last_posted = {}

    while True:
        now  = datetime.now(timezone.utc)
        hour = now.hour
        day  = now.date()

        if hour in POST_HOURS and last_posted.get(f"{day}_{hour}") != True:
            log.info("⏰ Trigger at %s UTC — running bot...", now.strftime("%H:%M"))
            try:
                await run()
                last_posted[f"{day}_{hour}"] = True
            except Exception as e:
                log.error("Bot run failed: %s", e)

        await asyncio.sleep(60)   # check every minute


if __name__ == "__main__":
    asyncio.run(scheduler())
