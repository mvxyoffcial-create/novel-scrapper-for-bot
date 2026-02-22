import asyncio
import logging

from pyrogram import Client, filters
from pyrogram.types import Message

import database as db
from config import Config
from script import script

logger = logging.getLogger(__name__)


def _is_owner(_, __, message: Message) -> bool:
    return message.from_user and message.from_user.id == Config.OWNER_ID


owner_filter = filters.create(_is_owner)


@Client.on_message(filters.command("stats") & owner_filter)
async def stats_handler(client: Client, message: Message):
    stats = await db.get_stats()
    text = script.STATS_TXT.format(
        users=stats["total_users"],
        active=stats["active"],
        novels=stats["novels"],
        chapters=stats["chapters"],
    )
    await message.reply_text(text)


@Client.on_message(filters.command("broadcast") & owner_filter)
async def broadcast_handler(client: Client, message: Message):
    if not message.reply_to_message:
        return await message.reply_text("Reply to the message you want to broadcast.")

    bcast_msg = message.reply_to_message
    wait      = await message.reply_text("📣 Broadcasting…")

    total = success = failed = 0
    async for user in await db.get_all_users():
        total += 1
        try:
            await bcast_msg.copy(user["_id"])
            success += 1
        except Exception:
            failed += 1
        await asyncio.sleep(0.05)

    await wait.edit_text(
        f"📣 Broadcast Done!\n\n"
        f"✅ Success : {success}\n"
        f"❌ Failed  : {failed}\n"
        f"👤 Total   : {total}"
    )
