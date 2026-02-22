"""Handles novel URL messages and novel-related callbacks."""
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
from utils.helpers import edit_progress, split_text
from utils.keyboards import chapter_nav_keyboard, novel_main_keyboard
from utils.exporters import export_txt, export_pdf, export_epub

logger = logging.getLogger(__name__)

URL_RE = re.compile(r"https?://[^\s]+", re.I)

# In-memory cache: user_id → Novel
_novel_cache: dict[int, Novel] = {}

# Track users waiting to input a chapter number: user_id → novel_url
_awaiting_chapter: dict[int, str] = {}


# ─── Any text message (not a command) ────────────────────────────────────────
@Client.on_message(filters.private & filters.text & ~filters.command(
    ["start", "help", "about", "search", "settings", "stats", "broadcast", "info"]
))
async def handle_text(client: Client, message: Message):
    user_id = message.from_user.id
    text    = message.text.strip()

    # Check if user is expected to send a chapter number
    if user_id in _awaiting_chapter:
        novel_url = _awaiting_chapter.pop(user_id)
        try:
            idx = int(text) - 1
        except ValueError:
            return await message.reply_text("❌ Please send a valid chapter number.")
        await _send_chapter(client, message, novel_url, idx)
        return

    # Check if it's a URL
    url = URL_RE.search(text)
    if url:
        await _handle_novel_url(client, message, url.group())
    else:
        await message.reply_text(
            "📖 Send me a novel URL to get started, or use /search <novel name>"
        )


# ─── Core: scrape novel from URL ─────────────────────────────────────────────
async def _handle_novel_url(client: Client, message: Message, url: str):
    user_id = message.from_user.id
    wait    = await message.reply_text("🔍 Analyzing novel URL, please wait…")

    try:
        async with NovelScraper() as scraper:
            novel = await scraper.scrape_novel(url)
    except Exception as e:
        logger.exception(e)
        return await wait.edit_text(f"❌ Scraper error: {e}")

    if not novel or not novel.chapters:
        return await wait.edit_text(
            "❌ Could not find any chapters at that URL.\n"
            "Try another link or check if the site is supported."
        )

    _novel_cache[user_id] = novel
    await db.save_progress(user_id, url, 0)
    await db.increment_novels_scraped()

    caption = (
        f"<b>📚 {novel.title}</b>\n\n"
        f"<b>📑 Total Chapters:</b> {len(novel.chapters)}\n"
        + (f"<b>✍️ Author:</b> {novel.author}\n" if novel.author else "") +
        f"\n{novel.description[:300] + '…' if len(novel.description) > 300 else novel.description}"
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


# ─── Core: send a chapter ────────────────────────────────────────────────────
async def _send_chapter(client, message_or_cb, novel_url: str, idx: int, edit: bool = False):
    is_cb   = isinstance(message_or_cb, CallbackQuery)
    user_id = message_or_cb.from_user.id

    novel = _novel_cache.get(user_id)
    if not novel:
        async with NovelScraper() as s:
            novel = await s.scrape_novel(novel_url)
        if not novel:
            txt = "❌ Could not reload novel."
            return await (message_or_cb.answer(txt, show_alert=True) if is_cb
                          else message_or_cb.reply_text(txt))
        _novel_cache[user_id] = novel

    total = len(novel.chapters)
    if idx < 0 or idx >= total:
        txt = f"❌ Chapter out of range. Novel has {total} chapters."
        return await (message_or_cb.answer(txt, show_alert=True) if is_cb
                      else message_or_cb.reply_text(txt))

    chapter = novel.chapters[idx]
    if not chapter.content:
        async with NovelScraper() as s:
            chapter = await s.fetch_chapter(chapter)
        novel.chapters[idx] = chapter

    await db.save_progress(user_id, novel_url, idx)
    await db.increment_chapters_sent()

    text = script.CHAPTER_TXT.format(
        title=novel.title,
        num=idx + 1,
        chap_title=chapter.title,
        content=chapter.content[:3500] if chapter.content else "_(content unavailable)_",
    )
    kb = chapter_nav_keyboard(novel_url, idx, total)

    if is_cb:
        try:
            await message_or_cb.message.edit_text(text, reply_markup=kb,
                                                  disable_web_page_preview=True)
        except Exception:
            await message_or_cb.message.reply_text(text, reply_markup=kb,
                                                   disable_web_page_preview=True)
    else:
        await message_or_cb.reply_text(text, reply_markup=kb, disable_web_page_preview=True)


# ─── Callbacks ───────────────────────────────────────────────────────────────
@Client.on_callback_query(filters.regex(r"^read\|"))
async def cb_read(client: Client, cb: CallbackQuery):
    _, url, idx_s = cb.data.split("|", 2)
    await cb.answer()
    await _send_chapter(client, cb, url, int(idx_s))


@Client.on_callback_query(filters.regex(r"^choose\|"))
async def cb_choose_chapter(client: Client, cb: CallbackQuery):
    url = cb.data.split("|", 1)[1]
    _awaiting_chapter[cb.from_user.id] = url
    await cb.answer()
    await cb.message.reply_text("📖 Send the chapter number you want to read:")


@Client.on_callback_query(filters.regex(r"^dl\|"))
async def cb_download(client: Client, cb: CallbackQuery):
    _, fmt, url = cb.data.split("|", 2)
    user_id     = cb.from_user.id
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
            chapters, progress_cb=progress_cb, delay=Config.CHAPTER_DELAY
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
            caption=f"📚 <b>{novel.title}</b>\n{len(chapters)} chapters",
        )
        os.remove(path)
    except Exception as e:
        logger.exception(e)
        await progress_msg.edit_text(f"❌ Export failed: {e}")


@Client.on_callback_query(filters.regex(r"^novel\|"))
async def cb_open_novel(client: Client, cb: CallbackQuery):
    url = cb.data.split("|", 1)[1]
    await cb.answer()
    await _handle_novel_url(client, cb.message, url)


@Client.on_callback_query(filters.regex("^close$"))
async def cb_close(client: Client, cb: CallbackQuery):
    await cb.answer()
    try:
        await cb.message.delete()
    except Exception:
        pass
