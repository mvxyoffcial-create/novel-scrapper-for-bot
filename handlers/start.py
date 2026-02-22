import asyncio
import logging

from pyrogram import Client, filters
from pyrogram.types import Message

import database as db
from config import Config
from script import script
from utils.helpers import check_force_sub, fetch_random_wallpaper
from utils.keyboards import force_sub_keyboard

logger = logging.getLogger(__name__)


@Client.on_message(filters.command("start") & filters.private)
async def start_handler(client: Client, message: Message):
    user = message.from_user
    await db.add_user(user.id, user.first_name)

    # ── Force-sub check ──────────────────────────────────────────
    if not await check_force_sub(client, user.id):
        await message.reply_photo(
            photo=Config.FORCE_SUB_IMAGE,
            caption=script.FORCE_SUB_TXT,
            reply_markup=force_sub_keyboard(),
        )
        return

    # ── Sticker (auto-delete after 2 s) ──────────────────────────
    try:
        sticker_msg = await message.reply_sticker(Config.START_STICKER)
        await asyncio.sleep(2)
        await sticker_msg.delete()
    except Exception:
        pass

    # ── Welcome photo ────────────────────────────────────────────
    welcome_text = script.START_TXT.format(user.mention)
    try:
        wp = await fetch_random_wallpaper()
        if wp:
            await message.reply_photo(photo=wp, caption=welcome_text)
        else:
            raise ValueError("no wallpaper")
    except Exception:
        try:
            await message.reply_photo(photo=Config.WELCOME_IMAGE, caption=welcome_text)
        except Exception:
            await message.reply_text(welcome_text)


@Client.on_message(filters.command("help") & filters.private)
async def help_handler(client: Client, message: Message):
    await message.reply_text(script.HELP_TXT, disable_web_page_preview=True)


@Client.on_message(filters.command("about") & filters.private)
async def about_handler(client: Client, message: Message):
    await message.reply_text(script.ABOUT_TXT, disable_web_page_preview=True)
