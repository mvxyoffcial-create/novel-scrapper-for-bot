import asyncio
import logging

from pyrogram import Client, filters
from pyrogram.types import Message

import database as db
from config import Config
from script import script
from utils.helpers import fetch_random_wallpaper

logger = logging.getLogger(__name__)


@Client.on_message(filters.command("start") & filters.private)
async def start_handler(client: Client, message: Message):
    user = message.from_user
    await db.add_user(user.id, user.first_name)

    # Sticker (auto-delete after 2s)
    try:
        sticker_msg = await message.reply_sticker(Config.START_STICKER)
        await asyncio.sleep(2)
        await sticker_msg.delete()
    except Exception as e:
        logger.warning(f"Sticker failed: {e}")

    welcome_text = script.START_TXT.format(user.mention)
    sent = False

    # Try random wallpaper
    try:
        wp = await fetch_random_wallpaper()
        if wp:
            await message.reply_photo(photo=wp, caption=welcome_text)
            sent = True
    except Exception as e:
        logger.warning(f"Wallpaper failed: {e}")

    # Fallback to static welcome image
    if not sent:
        try:
            await message.reply_photo(photo=Config.WELCOME_IMAGE, caption=welcome_text)
            sent = True
        except Exception as e:
            logger.warning(f"Welcome image failed: {e}")

    # Final fallback: plain text
    if not sent:
        await message.reply_text(welcome_text)


@Client.on_message(filters.command("help") & filters.private)
async def help_handler(client: Client, message: Message):
    await message.reply_text(script.HELP_TXT, disable_web_page_preview=True)


@Client.on_message(filters.command("about") & filters.private)
async def about_handler(client: Client, message: Message):
    await message.reply_text(script.ABOUT_TXT, disable_web_page_preview=True)
