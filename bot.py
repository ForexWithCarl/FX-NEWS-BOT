"""
FX Elite Desk — Automated Forex Factory News Bot (Fixed v3)
"""

import os
import asyncio
import logging
import aiohttp
import json
from datetime import datetime, timezone
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont

BOT_TOKEN  = os.environ["TELEGRAM_BOT_TOKEN"]
CHANNEL_ID = os.environ["TELEGRAM_CHANNEL_ID"]
GEMINI_KEY = os.environ.get("GEMINI_API_KEY", "")

FF_URL     = "https://nfs.faireconomy.media/ff_calendar_thisweek.json"
IMPACT_MAP = {"High": "🔴", "Medium": "🟡"}
HASHTAGS   = "#Forex #XAUUSDSignals #ForexNews #GoldTrading #TradingSignals"

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)


async def fetch_ff_events():
    try:
        async with aiohttp.ClientSession() as s:
            headers = {"User-Agent": "Mozilla/5.0"}
            async with s.get(FF_URL, headers=headers, timeout=aiohttp.ClientTimeout(total=30)) as r:
                data = json.loads(await r.text())
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        events = []
        for ev in data:
            try:
                if ev.get("date", "")[:10] == today and ev.get("impact") in ("High", "Medium"):
                    events.append({
                        "title":    ev.get("title", "N/A"),
                        "country":  ev.get("country", ""),
                        "impact":   ev.get("impact"),
                        "icon":     IMPACT_MAP.get(ev.get("impact"), "⚪"),
                        "date":     ev.get("date", ""),
                        "forecast": ev.get("forecast") or "—",
                        "previous": ev.get("previous") or "—",
                    })
            except Exception:
                continue
        return events
    except Exception as e:
        log.error("Fetch failed: %s", e)
        return []


async def rewrite_with_gemini(events):
    if not GEMINI_KEY or not events:
        return ""
    try:
        prompt = (
            "You are FX Elite Desk forex channel. Write a short Telegram post "
            "(max 80 words) about these economic events. Use emojis. "
            "End with XAU/USD tip. No special markdown symbols like | or *.\n\n"
            + json.dumps(events[:5])
        )
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash-latest:generateContent?key={GEMINI_KEY}"
        async with aiohttp.ClientSession() as s:
            async with s.post(url, json={"contents": [{"parts": [{"text": prompt}]}]},
                              timeout=aiohttp.ClientTimeout(total=20)) as r:
                resp = await r.json()
        return resp["candidates"][0]["content"]["parts"][0]["text"]
    except Exception as e:
        log.warning("Gemini failed: %s", e)
        return ""


def build_message(events, ai_text):
    now_str = datetime.now(timezone.utc).strftime("%d %b %Y")
    lines = [
        f"<b>📰 FOREX ECONOMIC NEWS — {now_str}</b>",
        "━━━━━━━━━━━━━━━━━━━━━━",
        "",
    ]

    if ai_text:
        lines.append(ai_text.strip())
        lines.append("")
        lines.append("━━━━━━━━━━━━━━━━━━━━━━")
        lines.append("<b>📋 Today's Key Events:</b>")
        lines.append("")

    if events:
        for ev in events:
            time_str = ""
            try:
                dt = datetime.fromisoformat(ev["date"].replace("Z", "+00:00"))
                time_str = dt.strftime("%I:%M %p UTC")
            except Exception:
                pass
            lines += [
                f"{ev['icon']} <b>{ev['title']}</b>",
                f"   🌍 {ev['country']}  ⏰ {time_str}",
                f"   📊 Forecast: {ev['forecast']}  Prev: {ev['previous']}",
                "",
            ]
    else:
        lines.append("✅ No major news today. Markets may be quiet — trade safe!")
        lines.append("")

    lines += [
        "━━━━━━━━━━━━━━━━━━━━━━",
        "⚡ <b>FX Elite Desk — Free XAU/USD Signals</b>",
        "👉 t.me/forex_factory_news_daily",
        "",
        HASHTAGS,
    ]
    return "\n".join(lines)


def generate_image(events):
    W, H = 900, max(480, 160 + len(events) * 56 + 60)
    BG   = (10, 12, 16)
    GOLD = (201, 150, 42)
    LGOLD= (245, 214, 122)
    WHITE= (230, 224, 200)
    GRAY = (100, 95, 75)
    RED  = (200, 20, 10)
    YELL = (210, 160, 20)
    DARK = (14, 16, 21)

    img  = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(img)

    draw.rectangle([(0,0),(W,4)], fill=GOLD)
    draw.rectangle([(0,4),(W,80)], fill=DARK)

    try:
        fb = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 22)
        fm = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 13)
        fs = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 11)
        fbd= ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 13)
    except Exception:
        fb = fm = fs = fbd = ImageFont.load_default()

    draw.text((28,18), "FX ELITE DESK", font=fb, fill=LGOLD)
    draw.text((28,50), "FREE XAU/USD SIGNALS  t.me/forex_factory_news_daily", font=fs, fill=GRAY)
    draw.rectangle([(710,18),(870,48)], fill=RED)
    draw.text((722,26), "BREAKING NEWS", font=fs, fill=WHITE)

    draw.rectangle([(0,80),(W,110)], fill=(14,15,20))
    now_str = datetime.now(timezone.utc).strftime("%d %B %Y")
    draw.text((28,90), f"  {now_str}  •  ECONOMIC CALENDAR  •  FOREX FACTORY", font=fs, fill=LGOLD)

    draw.rectangle([(0,110),(W,140)], fill=(18,20,26))
    cols = ["CCY","EVENT","IMPACT","TIME UTC","FORECAST","PREVIOUS"]
    cx   = [28, 95, 430, 555, 675, 785]
    for i,h in enumerate(cols):
        draw.text((cx[i],120), h, font=fs, fill=GRAY)
    draw.line([(0,140),(W,140)], fill=(42,37,16), width=1)

    y = 148
    for ev in events[:8]:
        rh = 54
        draw.rectangle([(0,y),(W,y+rh-2)], fill=(12,14,18))
        time_str = ""
        try:
            dt = datetime.fromisoformat(ev["date"].replace("Z","+00:00"))
            time_str = dt.strftime("%I:%M %p")
        except Exception:
            pass
        ic = RED if ev["impact"]=="High" else YELL
        draw.text((cx[0],y+8), ev["country"][:3], font=fbd, fill=GRAY)
        draw.text((cx[1],y+8), ev["title"][:36], font=fbd, fill=WHITE)
        draw.rectangle([(cx[2],y+6),(cx[2]+78,y+30)], outline=ic)
        draw.text((cx[2]+6,y+10), f"{ev['icon']} {ev['impact']}", font=fs, fill=ic)
        draw.text((cx[3],y+8), time_str, font=fm, fill=GRAY)
        draw.text((cx[4],y+8), str(ev["forecast"])[:8], font=fm, fill=GRAY)
        draw.text((cx[5],y+8), str(ev["previous"])[:8], font=fm, fill=GRAY)
        draw.line([(0,y+rh-2),(W,y+rh-2)], fill=(25,26,20), width=1)
        y += rh

    if not events:
        draw.text((28,165), "No major economic events today — trade safe!", font=fm, fill=GRAY)
        y = 220

    fy = y + 10
    draw.rectangle([(0,fy),(W,H)], fill=DARK)
    draw.line([(0,fy),(W,fy)], fill=(42,37,16), width=1)
    draw.text((28,fy+12), "Data: Forex Factory  •  Educational purposes only", font=fs, fill=GRAY)
    draw.text((630,fy+12), "t.me/forex_factory_news_daily", font=fs, fill=GOLD)

    buf = BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf


async def send_to_telegram(image_buf, caption):
    url  = f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto"
    data = aiohttp.FormData()
    data.add_field("chat_id",    CHANNEL_ID)
    data.add_field("caption",    caption)
    data.add_field("parse_mode", "HTML")
    data.add_field("photo", image_buf, filename="fx_news.png", content_type="image/png")

    async with aiohttp.ClientSession() as s:
        async with s.post(url, data=data) as r:
            resp = await r.json()
            if resp.get("ok"):
                log.info("✅ Posted to Telegram!")
            else:
                log.error("❌ Telegram error: %s", resp)
                await send_text_only(caption)


async def send_text_only(caption):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    async with aiohttp.ClientSession() as s:
        async with s.post(url, json={"chat_id": CHANNEL_ID, "text": caption, "parse_mode": "HTML"}) as r:
            resp = await r.json()
            if resp.get("ok"):
                log.info("✅ Text posted!")
            else:
                log.error("❌ Text failed: %s", resp)


async def run():
    log.info("🚀 Fetching Forex Factory events...")
    events  = await fetch_ff_events()
    log.info("Found %d events today", len(events))
    ai_text = await rewrite_with_gemini(events)
    caption = build_message(events, ai_text)
    log.info("🖼️ Generating image...")
    image_buf = generate_image(events)
    log.info("📤 Sending to Telegram...")
    await send_to_telegram(image_buf, caption)

if __name__ == "__main__":
    asyncio.run(run())
