"""
FX Elite Desk — Automated Forex Factory News Bot (Fixed Version)
Uses PIL for image generation instead of Playwright
"""

import os
import asyncio
import logging
import aiohttp
import json
from datetime import datetime, timezone
from io import BytesIO

# PIL for image generation
from PIL import Image, ImageDraw, ImageFont

BOT_TOKEN   = os.environ["TELEGRAM_BOT_TOKEN"]
CHANNEL_ID  = os.environ["TELEGRAM_CHANNEL_ID"]
GEMINI_KEY  = os.environ.get("GEMINI_API_KEY", "")

FF_URL = "https://nfs.faireconomy.media/ff_calendar_thisweek.json"

IMPACT_MAP = {"High": "🔴", "Medium": "🟡", "Low": "🟢"}
HASHTAGS   = "#Forex #XAUUSDSignals #ForexNews #GoldTrading #TradingSignals"

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)


# ─── FETCH NEWS ──────────────────────────────────────────────────────────────
async def fetch_ff_events() -> list:
    try:
        async with aiohttp.ClientSession() as session:
            headers = {"User-Agent": "Mozilla/5.0 (compatible; FXEliteBot/1.0)"}
            async with session.get(FF_URL, headers=headers, timeout=aiohttp.ClientTimeout(total=30)) as r:
                text = await r.text()
                data = json.loads(text)

        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        events = []
        for ev in data:
            try:
                ev_date = ev.get("date", "")[:10]
                impact  = ev.get("impact", "")
                if ev_date == today and impact in ("High", "Medium"):
                    events.append({
                        "title":    ev.get("title", "N/A"),
                        "country":  ev.get("country", ""),
                        "impact":   impact,
                        "icon":     IMPACT_MAP.get(impact, "⚪"),
                        "date":     ev.get("date", ""),
                        "forecast": ev.get("forecast") or "—",
                        "previous": ev.get("previous") or "—",
                    })
            except Exception as e:
                log.warning("Skipping event: %s", e)
                continue
        return events
    except Exception as e:
        log.error("Failed to fetch events: %s", e)
        return []


# ─── AI REWRITE ──────────────────────────────────────────────────────────────
async def rewrite_with_gemini(events: list) -> str:
    if not GEMINI_KEY or not events:
        return ""
    try:
        prompt = (
            "You are FX Elite Desk, a professional forex signal channel. "
            "Write a short engaging Telegram post (max 100 words) about these economic events. "
            "Use emojis. End with a brief XAU/USD tip. Events:\n\n"
            + json.dumps(events[:5], indent=2)
        )
        url = (
            "https://generativelanguage.googleapis.com/v1beta/models/"
            "gemini-1.5-flash-latest:generateContent?key=" + GEMINI_KEY
        )
        payload = {"contents": [{"parts": [{"text": prompt}]}]}
        async with aiohttp.ClientSession() as s:
            async with s.post(url, json=payload, timeout=aiohttp.ClientTimeout(total=20)) as r:
                resp = await r.json()
        return resp["candidates"][0]["content"]["parts"][0]["text"]
    except Exception as e:
        log.warning("Gemini failed: %s", e)
        return ""


# ─── BUILD MESSAGE ────────────────────────────────────────────────────────────
def build_message(events: list, ai_text: str) -> str:
    now_str = datetime.now(timezone.utc).strftime("%d %b %Y")
    lines = [
        f"📰 *FOREX ECONOMIC NEWS — {now_str}*",
        "━━━━━━━━━━━━━━━━━━━━━━",
        "",
    ]

    if ai_text:
        lines.append(ai_text.strip())
        lines.append("")
        lines.append("━━━━━━━━━━━━━━━━━━━━━━")
        lines.append("📋 *Today's Key Events:*")
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
                f"{ev['icon']} *{ev['title']}*",
                f"   🌍 {ev['country']} | ⏰ {time_str}",
                f"   📊 Forecast: {ev['forecast']}  |  Prev: {ev['previous']}",
                "",
            ]
    else:
        lines.append("✅ No major news today — markets may be quiet. Trade safe!")
        lines.append("")

    lines += [
        "━━━━━━━━━━━━━━━━━━━━━━",
        "⚡ *FX Elite Desk — Free XAU/USD Signals*",
        "👉 t\\.me/forex\\_factory\\_news\\_daily",
        "",
        HASHTAGS,
    ]
    return "\n".join(lines)


# ─── GENERATE IMAGE WITH PIL ─────────────────────────────────────────────────
def generate_image(events: list) -> BytesIO:
    W, H = 900, 500 + max(0, len(events) - 3) * 60

    # Colors
    BG      = (10, 12, 16)
    GOLD    = (201, 150, 42)
    LGOLD   = (245, 214, 122)
    WHITE   = (230, 224, 200)
    GRAY    = (100, 95, 75)
    RED     = (200, 20, 10)
    YELLOW  = (210, 160, 20)
    DARK    = (14, 16, 21)

    img  = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(img)

    # Gold accent bar top
    draw.rectangle([(0, 0), (W, 4)], fill=GOLD)

    # Header background
    draw.rectangle([(0, 4), (W, 80)], fill=DARK)

    # Brand name
    try:
        font_big   = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 22)
        font_med   = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 13)
        font_small = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 11)
        font_bold  = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 13)
    except Exception:
        font_big = font_med = font_small = font_bold = ImageFont.load_default()

    draw.text((28, 18), "⚡ FX ELITE DESK", font=font_big, fill=LGOLD)
    draw.text((28, 50), "FREE XAU/USD SIGNALS  •  t.me/forex_factory_news_daily", font=font_small, fill=GRAY)

    # Breaking news badge
    draw.rectangle([(720, 18), (870, 48)], fill=RED)
    draw.text((730, 26), "⚡ BREAKING", font=font_small, fill=WHITE)

    # Date strip
    draw.rectangle([(0, 80), (W, 110)], fill=(14, 15, 20))
    now_str = datetime.now(timezone.utc).strftime("%d %B %Y")
    draw.text((28, 90), f"📅 {now_str}  •  ECONOMIC CALENDAR  •  FOREX FACTORY", font=font_small, fill=LGOLD)

    # Table header
    draw.rectangle([(0, 110), (W, 140)], fill=(18, 20, 26))
    headers = ["CCY", "EVENT", "IMPACT", "TIME (UTC)", "FORECAST", "PREVIOUS"]
    col_x   = [28, 100, 430, 560, 680, 790]
    for i, h in enumerate(headers):
        draw.text((col_x[i], 120), h, font=font_small, fill=GRAY)

    # Divider
    draw.line([(0, 140), (W, 140)], fill=(42, 37, 16), width=1)

    # Rows
    y = 148
    for ev in events[:8]:
        row_h = 54
        draw.rectangle([(0, y), (W, y + row_h - 2)], fill=(12, 14, 18))

        time_str = ""
        try:
            dt = datetime.fromisoformat(ev["date"].replace("Z", "+00:00"))
            time_str = dt.strftime("%I:%M %p")
        except Exception:
            pass

        impact_color = RED if ev["impact"] == "High" else YELLOW

        draw.text((col_x[0], y + 8), ev["country"][:3], font=font_bold, fill=GRAY)
        draw.text((col_x[1], y + 8), ev["title"][:38], font=font_bold, fill=WHITE)

        # Impact badge
        badge_w = 80
        draw.rectangle([(col_x[2], y + 6), (col_x[2] + badge_w, y + 30)],
                        fill=(*impact_color[:3], 40) if len(impact_color) == 3 else impact_color,
                        outline=impact_color)
        draw.text((col_x[2] + 8, y + 10), f"{ev['icon']} {ev['impact']}", font=font_small, fill=impact_color)

        draw.text((col_x[3], y + 8), time_str, font=font_med, fill=GRAY)
        draw.text((col_x[4], y + 8), str(ev["forecast"])[:8], font=font_med, fill=GRAY)
        draw.text((col_x[5], y + 8), str(ev["previous"])[:8], font=font_med, fill=GRAY)

        draw.line([(0, y + row_h - 2), (W, y + row_h - 2)], fill=(25, 26, 20), width=1)
        y += row_h

    if not events:
        draw.text((28, 165), "✅ No major economic events today — markets may be quiet.", font=font_med, fill=GRAY)
        y = 220

    # Footer
    footer_y = max(y + 10, H - 44)
    draw.rectangle([(0, footer_y), (W, H)], fill=DARK)
    draw.line([(0, footer_y), (W, footer_y)], fill=(42, 37, 16), width=1)
    draw.text((28, footer_y + 12), "Data: Forex Factory  •  For educational purposes only", font=font_small, fill=GRAY)
    draw.text((650, footer_y + 12), "t.me/forex_factory_news_daily", font=font_small, fill=GOLD)

    buf = BytesIO()
    img.save(buf, format="PNG", quality=95)
    buf.seek(0)
    return buf


# ─── SEND TO TELEGRAM ────────────────────────────────────────────────────────
async def send_to_telegram(image_buf: BytesIO, caption: str):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto"
    data = aiohttp.FormData()
    data.add_field("chat_id", CHANNEL_ID)
    data.add_field("caption", caption)
    data.add_field("parse_mode", "MarkdownV2")
    data.add_field("photo", image_buf, filename="fx_news.png", content_type="image/png")

    async with aiohttp.ClientSession() as s:
        async with s.post(url, data=data) as r:
            resp = await r.json()
            if resp.get("ok"):
                log.info("✅ Posted to Telegram successfully!")
            else:
                log.error("❌ Telegram error: %s", resp)
                # Try sending text only if image fails
                await send_text_only(caption)


async def send_text_only(caption: str):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHANNEL_ID,
        "text": caption,
        "parse_mode": "MarkdownV2"
    }
    async with aiohttp.ClientSession() as s:
        async with s.post(url, json=payload) as r:
            resp = await r.json()
            if resp.get("ok"):
                log.info("✅ Text posted to Telegram!")
            else:
                log.error("❌ Text post failed: %s", resp)


# ─── MAIN ────────────────────────────────────────────────────────────────────
async def run():
    log.info("🚀 Fetching Forex Factory events...")
    events = await fetch_ff_events()
    log.info("Found %d events today", len(events))

    ai_text = await rewrite_with_gemini(events)
    caption = build_message(events, ai_text)

    log.info("🖼️ Generating image...")
    image_buf = generate_image(events)

    log.info("📤 Sending to Telegram...")
    await send_to_telegram(image_buf, caption)


if __name__ == "__main__":
    asyncio.run(run())
