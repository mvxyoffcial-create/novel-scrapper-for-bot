# 📚 Zero Novel Scraper Bot

A professional Telegram bot that lets users read and download web novels directly inside Telegram.

**Developer:** [@Venuboyy](https://t.me/Venuboyy) | **Channel:** [@zerodev2](https://t.me/zerodev2)

---

## ✨ Features

- 🔗 Paste any novel URL → bot fetches all chapters automatically
- 📖 Read chapters inline in Telegram (paginated with nav buttons)
- 📥 Download full novels as **TXT**, **PDF**, or **EPUB**
- 🔍 `/search <name>` to find novels across multiple sources
- ⚙️ Per-user settings (reading mode, auto-next, cover, download buttons)
- 🔒 Force-sub system (blocks users who haven't joined both channels)
- 📊 Admin stats + broadcast command
- 🌐 Health server on port 8080 (Koyeb-ready)

---

## 🚀 Quick Setup

### 1. Clone / Download
```bash
git clone <your-repo-url>
cd novel_bot
```

### 2. Install dependencies
```bash
pip install -r requirements.txt
```

### 3. Configure environment
```bash
cp .env.example .env
nano .env   # Fill in your values
```

Required values:
| Variable | Description |
|---|---|
| `API_ID` | From https://my.telegram.org |
| `API_HASH` | From https://my.telegram.org |
| `BOT_TOKEN` | From @BotFather |
| `MONGODB_URI` | MongoDB Atlas or self-hosted URI |

Optional:
| Variable | Description |
|---|---|
| `OWNER_ID` | Your Telegram numeric user ID |
| `PORT` | Web server port (default: 8080) |

### 4. Run
```bash
python bot.py
```

---

## ☁️ Deploy on Koyeb (Free Hosting)

1. Push this repo to GitHub
2. Go to [koyeb.com](https://koyeb.com) → **Create Service → GitHub**
3. Select your repo, set **Run command**: `python bot.py`
4. Add all env variables from `.env`
5. Set **Port** to `8080`
6. Deploy! ✅

---

## 📁 Project Structure

```
novel_bot/
├── bot.py              ← Main entry point
├── config.py           ← Configuration
├── database.py         ← MongoDB helpers
├── scraper.py          ← Web scraping engine
├── script.py           ← All bot text strings
├── requirements.txt
├── Procfile            ← Koyeb/Heroku deployment
├── .env.example
├── handlers/
│   ├── start.py        ← /start, /help, /about
│   ├── novel.py        ← Novel URL handling & reading
│   ├── search.py       ← /search command
│   ├── settings.py     ← /settings command
│   ├── admin.py        ← /stats, /broadcast
│   └── info.py         ← /info command
└── utils/
    ├── keyboards.py    ← All inline keyboards
    ├── helpers.py      ← Force-sub, progress, wallpaper
    └── exporters.py    ← TXT / PDF / EPUB export
```

---

## 🔧 Supported Novel Sources

- WordPress Madara theme sites
- MTL / Tomato-style chapter-list sites
- Sites with "Next Chapter" navigation buttons
- Generic sites with chapter links

---

## 📝 Commands

| Command | Description |
|---|---|
| `/start` | Welcome message |
| `/search <name>` | Search for a novel |
| `/settings` | Configure preferences |
| `/help` | Show help |
| `/about` | Bot info |
| `/info` | Show user info |
| `/stats` | _(Owner only)_ Bot statistics |
| `/broadcast` | _(Owner only)_ Send message to all users |
