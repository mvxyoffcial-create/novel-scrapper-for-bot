from pyrogram import Client, filters
from pyrogram.types import CallbackQuery, Message

import database as db
from script import script
from utils.keyboards import settings_keyboard


@Client.on_message(filters.command("settings") & filters.private)
async def settings_handler(client: Client, message: Message):
    settings = await db.get_settings(message.from_user.id)
    await message.reply_text(
        script.SETTINGS_TXT,
        reply_markup=settings_keyboard(settings),
    )


@Client.on_callback_query(filters.regex(r"^set\|"))
async def cb_settings(client: Client, cb: CallbackQuery):
    key     = cb.data.split("|", 1)[1]
    user_id = cb.from_user.id
    settings = await db.get_settings(user_id)

    if key == "reading_mode":
        new_val = "file" if settings["reading_mode"] == "telegram" else "telegram"
    else:
        new_val = not settings.get(key, True)

    await db.update_setting(user_id, key, new_val)
    settings[key] = new_val

    await cb.answer("✅ Setting updated!")
    await cb.message.edit_reply_markup(settings_keyboard(settings))
