"""Handles novel URL messages and novel-related callbacks."""
import asyncio
import logging
import os
import re
import time

from pyrogram import Client, filters
from pyrogram.types import CallbackQuery, Message

import database as db
from config import Config
from scraper import NovelScraper, Novel
from script import script
from utils.helpers import check_force_sub, edit_progress, split_text
from utils.keyboards import chapter_nav_keyboard, novel_main_keyboard, force_sub_keyboard
from utils.exporters import export_txt, export_pdf, export_epub

logger = logging.getLogger(__name__)

URL_RE = re.compile(r"https?://[^\s]+", re.I)

# In-memory cache: user_id → Novel
_novel_cache: dict[int, Novel] = {}


# ─── Detect novel URL message ────────────────────────────────────────────────
@Client.on_message(filters.private & filters.text & ~filters.command(
    ["start", "help", "about", "search", "settings", "stats", "broadcast", "info"]
))
async def handle_message(client: Client, message: Message):
    text = message.text or ""
    url  = URL_RE.search(text)

    if url:
        await _handle_novel_url(client, message, url.group())
    else:
        await message.reply_text("Please send a novel URL or use /search <name>.")


async def _handle_novel_url(client: Client, message: Message, url: str):
    user_id = message.from_user.id

    if not await check_force_sub(client, user_id):
        await message.reply_photo(
            photo=Config.FORCE_SUB_IMAGE,
            caption=script.FORCE_SUB_TXT,
            reply_markup=force_sub_keyboard(),
        )
        return

    wait = await message.reply_text("🔍 Analyzing novel URL, please wait…")

    async with NovelScraper() as scraper:
        novel = await scraper.scrape_novel(url)

    if not novel or not novel.chapters:
        await wait.edit_text("❌ Could not find any chapters at that URL. Try another link.")
        return

    _novel_cache[user_id] = novel
    await db.save_progress(user_id, url, 0)
    await db.increment_novels_scraped()

    caption = (
        f"<b>📚 {novel.title}</b>\n\n"
        f"<b>📑 Total Chapters:</b> {len(novel.chapters)}\n"
        f"{f'<b>✍️ Author:</b> {novel.author}' if novel.author else ''}\n\n"
        f"{novel.description[:300] + '…' if len(novel.description) > 300 else novel.description}"
    )

    kb = novel_main_keyboard(url, len(novel.chapters))

    try:
        if novel.cover_url:
            await wait.delete()
            await message.reply_photo(photo=novel.cover_url, caption=caption, reply_markup=kb)
        else:
            await wait.edit_text(caption, reply_markup=kb)
    except Exception:
        await wait.edit_text(caption, reply_markup=kb)


# ─── Callbacks ───────────────────────────────────────────────────────────────
@Client.on_callback_query(filters.regex(r"^read\|"))
async def cb_read(client: Client, cb: CallbackQuery):
    _, url, idx_s = cb.data.split("|", 2)
    idx     = int(idx_s)
    user_id = cb.from_user.id

    novel = _novel_cache.get(user_id)
    if not novel:
        async with NovelScraper() as s:
            novel = await s.scrape_novel(url)
        if not novel:
            return await cb.answer("❌ Could not load novel.", show_alert=True)
        _novel_cache[user_id] = novel

    if idx < 0 or idx >= len(novel.chapters):
        return await cb.answer("Invalid chapter index.", show_alert=True)

    await cb.answer()
    chapter = novel.chapters[idx]

    # Fetch chapter content if missing
    if not chapter.content:
        async with NovelScraper() as s:
            chapter = await s.fetch_chapter(chapter)
        novel.chapters[idx] = chapter

    await db.save_progress(user_id, url, idx)
    await db.increment_chapters_sent()

    text = script.CHAPTER_TXT.format(
        title=novel.title,
        num=idx + 1,
        chap_title=chapter.title,
        content=chapter.content[:3500] or "_(content unavailable)_",
    )

    kb = chapter_nav_keyboard(url, idx, len(novel.chapters))
    try:
        await cb.message.edit_text(text, reply_markup=kb, disable_web_page_preview=True)
    except Exception:
        await cb.message.reply_text(text, reply_markup=kb, disable_web_page_preview=True)


@Client.on_callback_query(filters.regex(r"^choose\|"))
async def cb_choose_chapter(client: Client, cb: CallbackQuery):
    url = cb.data.split("|", 1)[1]
    await cb.answer()
    await cb.message.reply_text(
        "📖 Send the chapter number you want to read.",
        reply_markup=None,
    )
    # Store in-flight state in DB
    await db.update_user(cb.from_user.id, {"_await_chapter_num": url})


@Client.on_message(filters.private & filters.text & ~filters.command(
    ["start", "help", "about", "search", "settings", "stats", "broadcast", "info"]
))
async def handle_chapter_number(client: Client, message: Message):
    user_id = message.from_user.id
    user    = await db.get_user(user_id)
    if not user or "_await_chapter_num" not in user:
        return  # not waiting

    url = user["_await_chapter_num"]
    await db.update_user(user_id, {"_await_chapter_num": None})

    try:
        idx = int(message.text.strip()) - 1
    except ValueError:
        return await message.reply_text("Please send a valid chapter number.")

    fake_cb_data = f"read|{url}|{idx}"
    # Reuse read callback logic
    novel = _novel_cache.get(user_id)
    if not novel:
        async with NovelScraper() as s:
            novel = await s.scrape_novel(url)
        if not novel:
            return await message.reply_text("❌ Could not reload novel.")
        _novel_cache[user_id] = novel

    if idx < 0 or idx >= len(novel.chapters):
        return await message.reply_text(
            f"❌ Chapter out of range. Novel has {len(novel.chapters)} chapters."
        )

    chapter = novel.chapters[idx]
    if not chapter.content:
        async with NovelScraper() as s:
            chapter = await s.fetch_chapter(chapter)
        novel.chapters[idx] = chapter

    await db.save_progress(user_id, url, idx)
    await db.increment_chapters_sent()

    text = script.CHAPTER_TXT.format(
        title=novel.title,
        num=idx + 1,
        chap_title=chapter.title,
        content=chapter.content[:3500] or "_(content unavailable)_",
    )
    kb = chapter_nav_keyboard(url, idx, len(novel.chapters))
    await message.reply_text(text, reply_markup=kb, disable_web_page_preview=True)


# ─── Download callbacks ───────────────────────────────────────────────────────
@Client.on_callback_query(filters.regex(r"^dl\|"))
async def cb_download(client: Client, cb: CallbackQuery):
    _, fmt, url = cb.data.split("|", 2)
    user_id     = cb.from_user.id

    if not await check_force_sub(client, user_id):
        return await cb.answer("Join channels first!", show_alert=True)

    await cb.answer()
    progress_msg = await cb.message.reply_text("📚 Fetching Chapters…")

    novel = _novel_cache.get(user_id)
    if not novel:
        async with NovelScraper() as s:
            novel = await s.scrape_novel(url)
        if not novel:
            return await progress_msg.edit_text("❌ Failed to load novel.")
        _novel_cache[user_id] = novel

    chapters = novel.chapters[:Config.MAX_CHAPTERS_PER_DL]
    start_ts = time.time()

    async def progress_cb(done, total):
        await edit_progress(progress_msg, done, total, start_ts)

    async with NovelScraper() as s:
        chapters = await s.fetch_chapters_batch(
            chapters,
            progress_cb=progress_cb,
            delay=Config.CHAPTER_DELAY,
        )

    novel.chapters[:len(chapters)] = chapters

    await progress_msg.edit_text(f"📦 Building {fmt.upper()} file…")

    try:
        if fmt == "txt":
            path = export_txt(novel, chapters)
        elif fmt == "pdf":
            path = export_pdf(novel, chapters)
        elif fmt == "epub":
            path = export_epub(novel, chapters)
        else:
            return await progress_msg.edit_text("Unknown format.")

        await progress_msg.delete()
        await cb.message.reply_document(
            document=path,
            caption=f"📚 **{novel.title}**\n{len(chapters)} chapters",
        )
        os.remove(path)
    except Exception as e:
        logger.exception(e)
        await progress_msg.edit_text(f"❌ Export failed: {e}")


# ─── Open novel from search result ──────────────────────────────────────────
@Client.on_callback_query(filters.regex(r"^novel\|"))
async def cb_open_novel(client: Client, cb: CallbackQuery):
    url = cb.data.split("|", 1)[1]
    await cb.answer()
    fake_msg = cb.message
    await _handle_novel_url(client, fake_msg, url)


# ─── Check sub callback ───────────────────────────────────────────────────────
@Client.on_callback_query(filters.regex("^check_sub$"))
async def cb_check_sub(client: Client, cb: CallbackQuery):
    if await check_force_sub(client, cb.from_user.id):
        await cb.answer("✅ Access granted!", show_alert=True)
        await cb.message.delete()
        # Re-trigger start
        await cb.message.reply_text(
            script.START_TXT.format(cb.from_user.mention)
        )
    else:
        await cb.answer("❌ You haven't joined all channels yet.", show_alert=True)


@Client.on_callback_query(filters.regex("^close$"))
async def cb_close(client: Client, cb: CallbackQuery):
    await cb.answer()
    try:
        await cb.message.delete()
    except Exception:
        pass
