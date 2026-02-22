"""
Zero Novel Scraper Bot
======================
Main entry point.

Setup:
  1. Fill in API_ID, API_HASH, BOT_TOKEN, MONGODB_URI in .env
  2. pip install -r requirements.txt
  3. python bot.py
"""
import asyncio
import logging
import os
from aiohttp import web

from pyrogram import Client
from config import Config

# ── Logging ──────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

# ── Pyrogram Client ──────────────────────────────────────────────────────────
plugins = {"root": "handlers"}

app = Client(
    name="NovelBot",
    api_id=Config.API_ID,
    api_hash=Config.API_HASH,
    bot_token=Config.BOT_TOKEN,
    plugins=plugins,
    sleep_threshold=60,
)

# ── Health-check web server (required for Koyeb port 8080) ───────────────────
async def health(_request: web.Request) -> web.Response:
    return web.Response(text="✅ Zero Novel Scraper Bot is running!", status=200)


async def start_web_server():
    web_app = web.Application()
    web_app.router.add_get("/", health)
    web_app.router.add_get("/health", health)
    runner = web.AppRunner(web_app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", Config.PORT)
    await site.start()
    logger.info(f"🌐 Health server running on port {Config.PORT}")


# ── Main ──────────────────────────────────────────────────────────────────────
async def main():
    logger.info("🚀 Starting Zero Novel Scraper Bot…")
    await start_web_server()
    async with app:
        me = await app.get_me()
        logger.info(f"✅ Bot started as @{me.username} (ID: {me.id})")
        await asyncio.Event().wait()   # run forever


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user.")
