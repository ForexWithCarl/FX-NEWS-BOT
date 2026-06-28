# FX Elite Desk — Automated Forex Factory News Bot
## Complete Setup Guide (Zero Budget)

---

## What This Bot Does
- Fetches **High & Medium impact** economic events from Forex Factory every day
- Generates a **professional dark-gold branded image** (like your reference screenshot)
- Rewrites the news **in your channel's own voice** (via free Gemini AI)
- Posts image + caption with hashtags to your **Telegram channel automatically**
- Runs **daily at 7:00 AM and 1:00 PM UTC** — no human needed

---

## Step 1 — Create Your Telegram Bot

1. Open Telegram → search **@BotFather**
2. Send `/newbot`
3. Name it: `FX Elite Desk News`
4. Username: `FXEliteDeskNewsBot` (anything ending in `bot`)
5. Copy the **token** (looks like: `7234567890:AAF...`)

**Add bot to your channel:**
- Open your channel → Settings → Administrators
- Add your new bot → give it **Post Messages** permission

---

## Step 2 — Get Free Gemini API Key (AI Rewriting)

1. Go to: https://aistudio.google.com/app/apikey
2. Click **Create API Key**
3. Copy it — it's free with generous limits

---

## Step 3 — Set Up on Free Hosting (Railway.app)

**Railway gives you 500 free hours/month — enough for 24/7 bot.**

1. Go to **railway.app** → Sign up free (use GitHub)
2. Click **New Project** → **Deploy from GitHub repo**
   - OR: Click **Empty Project** → **Add a Service** → **GitHub Repo**
3. Upload your bot files (or connect GitHub repo)
4. In Railway → your service → **Variables** tab, add:
   ```
   TELEGRAM_BOT_TOKEN  = your_token_here
   TELEGRAM_CHANNEL_ID = @FX_ELITE_DESK_XAU
   GEMINI_API_KEY      = your_gemini_key
   ```
5. In **Settings** → **Start Command**:
   ```
   python scheduler.py
   ```

---

## Step 3 (Alternative) — Run on Your Own VPS/PC

```bash
# Install Python 3.11+, then:
cd fx_news_bot

# Install dependencies
pip install -r requirements.txt

# Install Playwright browser
playwright install chromium

# Set environment variables
cp .env.example .env
nano .env          # fill in your values

# Run the scheduler (keeps running forever)
python scheduler.py
```

**Keep it running 24/7 with screen:**
```bash
screen -S fxbot
python scheduler.py
# Press Ctrl+A then D to detach
```

---

## Step 4 — Test It Immediately

```bash
# Run a single post right now (test)
python bot.py
```

Check your Telegram channel — you should see the news card posted!

---

## Post Format Preview

```
📰 FOREX ECONOMIC NEWS — 28 Jun 2026
━━━━━━━━━━━━━━━━━━━━━━

[AI rewritten summary in FX Elite Desk voice...]

━━━━━━━━━━━━━━━━━━━━━━
📋 Today's Key Events:

🔴 US Non-Farm Payrolls
   🌍 Country: USD
   ⏰ Time: 12:30 PM UTC
   📊 Forecast: 185K  |  Previous: 177K

🟡 Canada Ivey PMI
   🌍 Country: CAD
   ⏰ Time: 02:00 PM UTC
   📊 Forecast: 52.4  |  Previous: 51.8

━━━━━━━━━━━━━━━━━━━━━━
⚡ FX Elite Desk — Free XAU/USD Signals
👉 Join: t.me/FX_ELITE_DESK_XAU

#Forex #XAUUSDSignals #ForexNews #GoldTrading #TradingSignals
```

---

## Troubleshooting

| Problem | Fix |
|---|---|
| `TELEGRAM_BOT_TOKEN not set` | Check your .env file |
| Bot posts but no image | Run `playwright install chromium` |
| No events showing | Forex Factory may have no major news today (normal) |
| Telegram 400 error | Make sure bot is admin in your channel |
| Gemini not working | Check API key; leave blank to skip AI rewrite |

---

## Files in This Project

```
fx_news_bot/
├── bot.py           ← Main bot (fetch + image + post)
├── scheduler.py     ← Runs bot daily automatically
├── requirements.txt ← Python packages
├── .env.example     ← Copy to .env and fill values
└── README.md        ← This guide
```

---

*Built for FX Elite Desk | t.me/FX_ELITE_DESK_XAU*
