from pyrogram import Client, filters
from pyrogram.types import Message

import database as db
from scraper import search_novels
from utils.keyboards import search_results_keyboard
from script import script


@Client.on_message(filters.command("search") & filters.private)
async def search_handler(client: Client, message: Message):
    await db.add_user(message.from_user.id, message.from_user.first_name)

    query = " ".join(message.command[1:]).strip()
    if not query:
        return await message.reply_text("Usage: <code>/search novel name</code>")

    wait    = await message.reply_text(f"🔍 Searching for: <b>{query}</b>…")
    results = await search_novels(query)

    if not results:
        return await wait.edit_text(
            f"❌ No results found for <b>{query}</b>.\n"
            "Try a different keyword or paste a direct novel URL."
        )

    text = f"<b>🔎 Results for: {query}</b>\n\n"
    for i, r in enumerate(results, 1):
        text += f"{i}. <b>{r.title}</b>\n"

    await wait.edit_text(text, reply_markup=search_results_keyboard(results))
