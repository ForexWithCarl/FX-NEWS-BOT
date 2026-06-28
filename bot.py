"""
FX Elite Desk — Automated Forex Factory News Bot
Fetches economic calendar from Forex Factory RSS feed,
generates a news image, and posts to Telegram channel.
"""

import os
import asyncio
import logging
import feedparser
import aiohttp
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from html import unescape
from playwright.async_api import async_playwright

# ─── CONFIG ──────────────────────────────────────────────────────────────────
BOT_TOKEN   = os.environ["TELEGRAM_BOT_TOKEN"]       # set in .env
CHANNEL_ID  = os.environ["TELEGRAM_CHANNEL_ID"]      # e.g. @FX_ELITE_DESK_XAU
GEMINI_KEY  = os.environ.get("GEMINI_API_KEY", "")   # optional AI rewrite

FF_RSS_URL  = "https://nfs.faireconomy.media/ff_calendar_thisweek.json"
# Forex Factory publishes their calendar as open JSON — no scraping needed.

IMPACT_MAP  = {"High": "🔴", "Medium": "🟡", "Low": "🟢", "Holiday": "⚪"}
HASHTAGS    = "#Forex #XAUUSDSignals #ForexNews #GoldTrading #TradingSignals"

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

# ─── FETCH NEWS ──────────────────────────────────────────────────────────────
async def fetch_ff_events() -> list[dict]:
    """Pull today's High/Medium impact events from Forex Factory calendar JSON."""
    async with aiohttp.ClientSession() as session:
        async with session.get(FF_RSS_URL, timeout=aiohttp.ClientTimeout(total=20)) as r:
            data = await r.json(content_type=None)

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    events = []
    for ev in data:
        try:
            ev_date = ev.get("date", "")[:10]  # "2026-06-28T..."
            impact  = ev.get("impact", "")
            if ev_date == today and impact in ("High", "Medium"):
                events.append({
                    "title":    ev.get("title", ""),
                    "country":  ev.get("country", ""),
                    "impact":   impact,
                    "icon":     IMPACT_MAP.get(impact, "⚪"),
                    "date":     ev.get("date", ""),
                    "forecast": ev.get("forecast", "—"),
                    "previous": ev.get("previous", "—"),
                })
        except Exception:
            continue
    return events


# ─── AI REWRITE (optional Gemini) ────────────────────────────────────────────
async def rewrite_with_gemini(events: list[dict]) -> str:
    """Use Gemini free tier to rephrase the news in channel's own voice."""
    if not GEMINI_KEY:
        return ""
    prompt = (
        "You are the voice of FX Elite Desk, a professional forex signal channel. "
        "Rewrite the following economic calendar events into ONE short, engaging "
        "Telegram post (max 200 words). Do NOT copy exact wording. Use emojis naturally. "
        "End with a brief trading tip for gold (XAU/USD). Events:\n\n"
        + json.dumps(events, indent=2)
    )
    url = (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        "gemini-1.5-flash-latest:generateContent?key=" + GEMINI_KEY
    )
    payload = {"contents": [{"parts": [{"text": prompt}]}]}
    async with aiohttp.ClientSession() as s:
        async with s.post(url, json=payload) as r:
            resp = await r.json()
    try:
        return resp["candidates"][0]["content"]["parts"][0]["text"]
    except Exception:
        return ""


# ─── BUILD MESSAGE TEXT ───────────────────────────────────────────────────────
def build_message(events: list[dict], ai_text: str) -> str:
    now_str = datetime.now(timezone.utc).strftime("%d %b %Y")
    lines = [
        f"📰 *FOREX ECONOMIC NEWS — {now_str}*",
        f"━━━━━━━━━━━━━━━━━━━━━━",
        "",
    ]

    if ai_text:
        lines.append(ai_text.strip())
        lines.append("")
        lines.append("━━━━━━━━━━━━━━━━━━━━━━")
        lines.append("📋 *Today's Key Events:*")
        lines.append("")

    for ev in events:
        time_str = ""
        try:
            dt = datetime.fromisoformat(ev["date"].replace("Z", "+00:00"))
            time_str = dt.strftime("%I:%M %p UTC")
        except Exception:
            pass

        lines += [
            f"{ev['icon']} *{ev['title']}*",
            f"   🌍 Country: {ev['country']}",
            f"   ⏰ Time: {time_str}",
            f"   📊 Forecast: {ev['forecast']}  |  Previous: {ev['previous']}",
            "",
        ]

    if not events:
        lines.append("✅ No high-impact news today. Markets may be quiet — trade safe!")
        lines.append("")

    lines += [
        "━━━━━━━━━━━━━━━━━━━━━━",
        "⚡ *FX Elite Desk — Free XAU/USD Signals*",
        "👉 Join: t.me/FX\\_ELITE\\_DESK\\_XAU",
        "",
        HASHTAGS,
    ]
    return "\n".join(lines)


# ─── GENERATE IMAGE ──────────────────────────────────────────────────────────
def build_html(events: list[dict]) -> str:
    now_str = datetime.now(timezone.utc).strftime("%d %B %Y")
    rows = ""
    for ev in events[:8]:
        time_str = ""
        try:
            dt = datetime.fromisoformat(ev["date"].replace("Z", "+00:00"))
            time_str = dt.strftime("%I:%M %p")
        except Exception:
            pass
        impact_cls = "high" if ev["impact"] == "High" else "med"
        rows += f"""
        <tr>
          <td class="flag">{ev['country']}</td>
          <td class="title-cell">{ev['title']}</td>
          <td><span class="badge {impact_cls}">{ev['icon']} {ev['impact']}</span></td>
          <td class="num">{time_str}</td>
          <td class="num">{ev['forecast']}</td>
          <td class="num">{ev['previous']}</td>
        </tr>"""

    if not rows:
        rows = "<tr><td colspan='6' style='text-align:center;padding:20px;color:#aaa;'>No major events today</td></tr>"

    return f"""<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<style>
  @import url('https://fonts.googleapis.com/css2?family=Barlow+Condensed:wght@400;600;700&family=Barlow:wght@400;500&display=swap');

  * {{ margin:0; padding:0; box-sizing:border-box; }}

  body {{
    width: 900px;
    background: #0a0c10;
    font-family: 'Barlow', sans-serif;
    color: #e8e0cc;
    overflow: hidden;
  }}

  .card {{
    width: 900px;
    background: linear-gradient(160deg, #0f1218 0%, #0a0c10 60%);
    border: 1px solid #2a2510;
    position: relative;
    overflow: hidden;
  }}

  /* Gold accent bar top */
  .accent-bar {{
    height: 4px;
    background: linear-gradient(90deg, #c9962a, #f5d67a, #c9962a);
  }}

  /* Header */
  .header {{
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 20px 28px 16px;
    border-bottom: 1px solid #1e1c14;
  }}
  .brand {{
    display: flex;
    align-items: center;
    gap: 12px;
  }}
  .brand-icon {{
    width: 44px; height: 44px;
    background: linear-gradient(135deg, #c9962a, #f5d67a);
    border-radius: 10px;
    display: flex; align-items: center; justify-content: center;
    font-size: 22px;
  }}
  .brand-text h1 {{
    font-family: 'Barlow Condensed', sans-serif;
    font-size: 20px; font-weight: 700;
    color: #f5d67a;
    letter-spacing: 1px;
    text-transform: uppercase;
  }}
  .brand-text p {{
    font-size: 11px;
    color: #8a7f60;
    letter-spacing: 0.5px;
  }}

  .headline-badge {{
    background: linear-gradient(135deg, #c9140a, #8b0000);
    color: white;
    font-family: 'Barlow Condensed', sans-serif;
    font-size: 13px; font-weight: 700;
    letter-spacing: 2px;
    padding: 6px 14px;
    border-radius: 4px;
    text-transform: uppercase;
    animation: none;
    border: 1px solid #e32;
  }}

  .date-strip {{
    background: #0e1015;
    padding: 10px 28px;
    display: flex;
    align-items: center;
    gap: 8px;
    border-bottom: 1px solid #1e1c14;
  }}
  .date-strip span {{
    font-family: 'Barlow Condensed', sans-serif;
    font-size: 15px;
    color: #f5d67a;
    letter-spacing: 1px;
  }}
  .date-strip .dot {{
    width: 5px; height: 5px;
    background: #c9962a;
    border-radius: 50%;
  }}

  /* Table */
  .table-wrap {{ padding: 16px 28px 20px; }}

  table {{
    width: 100%;
    border-collapse: collapse;
  }}
  thead tr {{
    border-bottom: 1px solid #2a2510;
  }}
  thead th {{
    font-family: 'Barlow Condensed', sans-serif;
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 1.5px;
    color: #8a7f60;
    text-transform: uppercase;
    padding: 0 0 10px;
    text-align: left;
  }}
  thead th.num {{ text-align: right; }}

  tbody tr {{
    border-bottom: 1px solid #13140e;
    transition: background 0.15s;
  }}
  tbody tr:last-child {{ border-bottom: none; }}

  td {{
    padding: 11px 0;
    font-size: 13.5px;
    vertical-align: middle;
  }}
  td.flag {{
    font-size: 12px;
    color: #8a7f60;
    width: 52px;
    font-family: 'Barlow Condensed', sans-serif;
    letter-spacing: 0.5px;
    font-weight: 600;
  }}
  td.title-cell {{
    font-size: 13px;
    font-weight: 500;
    color: #ddd8c0;
    padding-right: 16px;
  }}
  td.num {{
    text-align: right;
    font-family: 'Barlow Condensed', sans-serif;
    font-size: 13px;
    color: #a09060;
  }}

  .badge {{
    display: inline-block;
    padding: 3px 9px;
    border-radius: 4px;
    font-family: 'Barlow Condensed', sans-serif;
    font-size: 12px;
    font-weight: 600;
    letter-spacing: 0.5px;
  }}
  .badge.high {{ background: rgba(200,20,10,0.18); color: #ff6b5b; border: 1px solid rgba(200,20,10,0.4); }}
  .badge.med  {{ background: rgba(210,160,20,0.15); color: #f5c842; border: 1px solid rgba(210,160,20,0.3); }}

  /* Footer */
  .footer {{
    background: #0e1015;
    border-top: 1px solid #1e1c14;
    padding: 12px 28px;
    display: flex;
    align-items: center;
    justify-content: space-between;
  }}
  .footer-left {{
    font-size: 11px;
    color: #5a5240;
  }}
  .footer-right {{
    font-family: 'Barlow Condensed', sans-serif;
    font-size: 13px;
    color: #c9962a;
    letter-spacing: 0.5px;
  }}

  /* Decorative glow */
  .glow {{
    position: absolute;
    top: -60px; right: -60px;
    width: 200px; height: 200px;
    background: radial-gradient(circle, rgba(201,150,42,0.08) 0%, transparent 70%);
    pointer-events: none;
  }}
</style>
</head>
<body>
<div class="card">
  <div class="glow"></div>
  <div class="accent-bar"></div>

  <div class="header">
    <div class="brand">
      <div class="brand-icon">⚡</div>
      <div class="brand-text">
        <h1>FX Elite Desk</h1>
        <p>FREE XAU/USD SIGNALS • t.me/FX_ELITE_DESK_XAU</p>
      </div>
    </div>
    <div class="headline-badge">⚡ BREAKING NEWS</div>
  </div>

  <div class="date-strip">
    <span>📅 {now_str}</span>
    <div class="dot"></div>
    <span style="color:#8a7f60;">ECONOMIC CALENDAR</span>
    <div class="dot"></div>
    <span style="color:#8a7f60;">FOREX FACTORY</span>
  </div>

  <div class="table-wrap">
    <table>
      <thead>
        <tr>
          <th>CCY</th>
          <th>Event</th>
          <th>Impact</th>
          <th class="num">Time (UTC)</th>
          <th class="num">Forecast</th>
          <th class="num">Previous</th>
        </tr>
      </thead>
      <tbody>
        {rows}
      </tbody>
    </table>
  </div>

  <div class="footer">
    <span class="footer-left">Data sourced from Forex Factory • For educational purposes only</span>
    <span class="footer-right">t.me/FX_ELITE_DESK_XAU</span>
  </div>
</div>
</body>
</html>"""


async def render_image(html: str, out_path: str):
    """Use Playwright headless Chromium to screenshot the HTML card."""
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page    = await browser.new_page(viewport={"width": 900, "height": 600})
        await page.set_content(html, wait_until="networkidle")
        # Clip to actual card height
        card = await page.query_selector(".card")
        bb   = await card.bounding_box()
        await page.screenshot(
            path=out_path,
            clip={"x": bb["x"], "y": bb["y"],
                  "width": bb["width"], "height": bb["height"]},
        )
        await browser.close()
    log.info("Image saved: %s", out_path)


# ─── SEND TO TELEGRAM ─────────────────────────────────────────────────────────
async def send_to_telegram(image_path: str, caption: str):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto"
    with open(image_path, "rb") as f:
        data = aiohttp.FormData()
        data.add_field("chat_id", CHANNEL_ID)
        data.add_field("caption", caption)
        data.add_field("parse_mode", "Markdown")
        data.add_field("photo", f, filename="news.png", content_type="image/png")
        async with aiohttp.ClientSession() as s:
            async with s.post(url, data=data) as r:
                resp = await r.json()
                if resp.get("ok"):
                    log.info("✅ Posted to Telegram!")
                else:
                    log.error("Telegram error: %s", resp)


# ─── MAIN ─────────────────────────────────────────────────────────────────────
async def run():
    log.info("🚀 Fetching Forex Factory events...")
    events = await fetch_ff_events()
    log.info("Found %d events today", len(events))

    # AI rewrite (optional)
    ai_text = await rewrite_with_gemini(events)

    # Build message
    caption = build_message(events, ai_text)

    # Generate image
    html      = build_html(events)
    img_path  = "/tmp/fx_news.png"
    await render_image(html, img_path)

    # Post to Telegram
    await send_to_telegram(img_path, caption)


if __name__ == "__main__":
    asyncio.run(run())
