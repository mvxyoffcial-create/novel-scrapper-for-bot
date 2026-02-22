import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # ─── Bot Credentials ──────────────────────────────────────────
    API_ID        = int(os.environ.get("API_ID", 0))
    API_HASH      = os.environ.get("API_HASH", "")
    BOT_TOKEN     = os.environ.get("BOT_TOKEN", "")
    MONGODB_URI   = os.environ.get("MONGODB_URI", "")

    # ─── Force-Sub Channels ───────────────────────────────────────
    FORCE_SUB_CHANNELS = [
        {"id": "@zerodev2",       "link": "https://t.me/zerodev2",       "name": "ZeroDev"},
        {"id": "@mvxyoffcail",    "link": "https://t.me/mvxyoffcail",    "name": "MvxyOfficial"},
    ]

    # ─── Owner ────────────────────────────────────────────────────
    OWNER_ID      = int(os.environ.get("OWNER_ID", 0))
    OWNER_USERNAME = "Venuboyy"

    # ─── Assets ───────────────────────────────────────────────────
    START_STICKER  = "CAACAgIAAxkBAAEQZtFpgEdROhGouBVFD3e0K-YjmVHwsgACtCMAAphLKUjeub7NKlvk2TgE"
    WALLPAPER_API  = "https://api.aniwallpaper.workers.dev/random?type=girl"
    FORCE_SUB_IMAGE = "https://i.ibb.co/pr2H8cwT/img-8312532076.jpg"
    WELCOME_IMAGE   = "https://i.ibb.co/KpDjCfFx/img-8108646188.jpg"

    # ─── Web server ───────────────────────────────────────────────
    PORT = int(os.environ.get("PORT", 8080))

    # ─── Limits ───────────────────────────────────────────────────
    MAX_CHAPTERS_PER_DL = 500
    CHAPTER_DELAY       = 0.3   # seconds between requests
