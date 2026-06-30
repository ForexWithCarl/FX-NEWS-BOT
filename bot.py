"""
FX Elite Desk — Real-Time Forex News Alert Bot (v2)
Posts economic news 10-15 minutes BEFORE the event happens — matching the
proven "Trading News Daily" channel format. Runs every 5 minutes via scheduler.
"""

import os
import asyncio
import logging
import aiohttp
import json
from datetime import datetime, timezone, timedelta
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont

BOT_TOKEN  = os.environ["TELEGRAM_BOT_TOKEN"]
CHANNEL_ID = os.environ["TELEGRAM_CHANNEL_ID"]

FF_URL = "https://nfs.faireconomy.media/ff_calendar_thisweek.json"

# Alert window — post events that start within this many minutes from now
ALERT_WINDOW_MIN = 15

IMPACT_EMOJI = {"High": "🔴", "Medium": "🟠", "Low": "🟢"}
COUNTRY_FLAG = {
    "USD": "🇺🇸", "EUR": "🇪🇺", "GBP": "🇬🇧", "JPY": "🇯🇵", "AUD": "🇦🇺",
    "CAD": "🇨🇦", "CHF": "🇨🇭", "NZD": "🇳🇿", "CNY": "🇨🇳",
}

HASHTAGS = "#Forex #ForexNews #XAUUSD #Trading #EconomicCalendar"

# In-memory set of already-posted event keys (resets on container restart, fine for daily cycle)
_posted_keys = set()

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)


# ─── FETCH EVENTS ─────────────────────────────────────────────────────────────
async def fetch_upcoming_events():
    try:
        async with aiohttp.ClientSession() as s:
            headers = {"User-Agent": "Mozilla/5.0"}
            async with s.get(FF_URL, headers=headers, timeout=aiohttp.ClientTimeout(total=30)) as r:
                data = json.loads(await r.text())
    except Exception as e:
        log.error("Fetch failed: %s", e)
        return []

    now = datetime.now(timezone.utc)
    window_end = now + timedelta(minutes=ALERT_WINDOW_MIN)

    due = []
    for ev in data:
        try:
            impact = ev.get("impact")
            if impact not in ("High", "Medium"):
                continue
            ev_dt = datetime.fromisoformat(ev["date"].replace("Z", "+00:00"))
            if now <= ev_dt <= window_end:
                key = f"{ev.get('title')}_{ev.get('country')}_{ev['date']}"
                if key in _posted_keys:
                    continue
                due.append({
                    "key":      key,
                    "title":    ev.get("title", "N/A"),
                    "country":  ev.get("country", ""),
                    "impact":   impact,
                    "date":     ev["date"],
                    "forecast": ev.get("forecast") or "—",
                    "previous": ev.get("previous") or "—",
                })
        except Exception:
            continue
    return due


# ─── BUILD MESSAGE (matches reference channel style) ─────────────────────────
def build_message(events: list) -> str:
    if not events:
        return ""

    # All grouped events share roughly the same time window
    first_dt = datetime.fromisoformat(events[0]["date"].replace("Z", "+00:00"))
    minutes_left = max(1, int((first_dt - datetime.now(timezone.utc)).total_seconds() // 60))

    lines = ["#News", ""]

    for ev in events:
        flag = COUNTRY_FLAG.get(ev["country"], "🌍")
        dt   = datetime.fromisoformat(ev["date"].replace("Z", "+00:00"))
        date_str = dt.strftime("%-m/%-d/%Y %I:%M %p")

        lines += [
            f"Impact: {IMPACT_EMOJI.get(ev['impact'], '⚪')} {ev['impact']}",
            f"Country: {flag} {ev['country']}",
            f"Title: 📌 {ev['title']}",
            f"Date: 📅 {date_str}",
            f"Forecast: {ev['forecast']}",
            f"Previous: {ev['previous']}",
            "",
        ]

    lines += [
        f"⏰: Max {minutes_left} Minute until news!",
        "",
        "👉 t.me/forex_factory_news_daily",
        "",
        HASHTAGS,
        "",
        "⚡ Looking for reliable XAU/USD signals?",
        "Join FX Elite Desk free — link below! 👇",
    ]
    return "\n".join(lines)


# ─── GENERATE REUSABLE BREAKING-NEWS BANNER ──────────────────────────────────
def generate_banner() -> BytesIO:
    W, H = 1000, 420
    img  = Image.new("RGB", (W, H), (8, 10, 16))
    draw = ImageDraw.Draw(img)

    # Diagonal navy/blue tech background strips
    for i in range(-H, W, 26):
        draw.line([(i, 0), (i + H, H)], fill=(16, 22, 36), width=10)

    try:
        f_huge = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 70)
        f_med  = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 26)
        f_sml  = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 18)
    except Exception:
        f_huge = f_med = f_sml = ImageFont.load_default()

    # Red "BREAKING" banner
    draw.polygon([(0, 70), (560, 70), (520, 150), (0, 150)], fill=(201, 20, 10))
    draw.text((40, 86), "BREAKING", font=f_huge, fill=(255, 255, 255))

    # White "NEWS" banner
    draw.polygon([(0, 170), (650, 170), (690, 260), (0, 260)], fill=(245, 245, 245))
    draw.text((40, 188), "NEWS", font=f_huge, fill=(15, 20, 30))

    # Right-side tagline
    draw.text((700, 190), "STAY INFORMED,", font=f_med, fill=(230, 230, 230))
    draw.text((700, 222), "STAY AHEAD", font=f_med, fill=(230, 230, 230))

    # Bottom red accent strips
    draw.rectangle([(640, 290), (760, 310)], fill=(201, 20, 10))
    draw.rectangle([(770, 290), (940, 310)], fill=(201, 20, 10))

    # Footer brand
    draw.text((40, 360), "FX ELITE DESK  •  t.me/forex_factory_news_daily", font=f_sml, fill=(150, 150, 150))

    buf = BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf


# ─── SEND TO TELEGRAM ─────────────────────────────────────────────────────────
async def send_alert(events: list):
    caption   = build_message(events)
    image_buf = generate_banner()

    url  = f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto"
    data = aiohttp.FormData()
    data.add_field("chat_id", CHANNEL_ID)
    data.add_field("caption", caption)
    data.add_field("photo", image_buf, filename="breaking_news.png", content_type="image/png")

    async with aiohttp.ClientSession() as s:
        async with s.post(url, data=data) as r:
            resp = await r.json()
            if resp.get("ok"):
                log.info("✅ Alert posted for %d event(s)", len(events))
                for ev in events:
                    _posted_keys.add(ev["key"])
            else:
                log.error("❌ Telegram error: %s", resp)


# ─── MAIN CHECK CYCLE ─────────────────────────────────────────────────────────
async def run_check():
    events = await fetch_upcoming_events()
    if not events:
        log.info("No events due in next %d minutes", ALERT_WINDOW_MIN)
        return

    # Group events that share the exact same timestamp into one post
    groups = {}
    for ev in events:
        groups.setdefault(ev["date"], []).append(ev)

    for date_key, group in groups.items():
        await send_alert(group)


if __name__ == "__main__":
    asyncio.run(run_check())
