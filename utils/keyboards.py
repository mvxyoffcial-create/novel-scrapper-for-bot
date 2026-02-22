from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from config import Config


def force_sub_keyboard() -> InlineKeyboardMarkup:
    buttons = []
    for ch in Config.FORCE_SUB_CHANNELS:
        buttons.append([InlineKeyboardButton(f"📢 Join {ch['name']}", url=ch["link"])])
    buttons.append([InlineKeyboardButton("✅ I Joined", callback_data="check_sub")])
    return InlineKeyboardMarkup(buttons)


def novel_main_keyboard(novel_url: str, total_chapters: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("📖 First Chapter",  callback_data=f"read|{novel_url}|0"),
            InlineKeyboardButton("📖 Latest Chapter", callback_data=f"read|{novel_url}|{total_chapters-1}"),
        ],
        [
            InlineKeyboardButton("🔢 Choose Chapter", callback_data=f"choose|{novel_url}"),
        ],
        [
            InlineKeyboardButton("📄 TXT",  callback_data=f"dl|txt|{novel_url}"),
            InlineKeyboardButton("📕 PDF",  callback_data=f"dl|pdf|{novel_url}"),
            InlineKeyboardButton("📚 EPUB", callback_data=f"dl|epub|{novel_url}"),
        ],
    ])


def chapter_nav_keyboard(novel_url: str, current: int, total: int) -> InlineKeyboardMarkup:
    row = []
    if current > 0:
        row.append(InlineKeyboardButton("⬅️ Prev", callback_data=f"read|{novel_url}|{current-1}"))
    row.append(InlineKeyboardButton("❌ Close", callback_data="close"))
    if current < total - 1:
        row.append(InlineKeyboardButton("Next ➡️", callback_data=f"read|{novel_url}|{current+1}"))
    return InlineKeyboardMarkup([row])


def settings_keyboard(settings: dict) -> InlineKeyboardMarkup:
    mode     = "📱 Telegram" if settings["reading_mode"] == "telegram" else "📁 File"
    auto_next = "✅ ON" if settings["auto_next"] else "❌ OFF"
    cover    = "✅ ON" if settings["send_cover"] else "❌ OFF"
    dl_btns  = "✅ ON" if settings["download_buttons"] else "❌ OFF"

    return InlineKeyboardMarkup([
        [InlineKeyboardButton(f"📖 Reading Mode: {mode}", callback_data="set|reading_mode")],
        [InlineKeyboardButton(f"⏭ Auto Next: {auto_next}",       callback_data="set|auto_next")],
        [InlineKeyboardButton(f"🖼 Send Cover: {cover}",          callback_data="set|send_cover")],
        [InlineKeyboardButton(f"⬇️ DL Buttons: {dl_btns}",       callback_data="set|download_buttons")],
        [InlineKeyboardButton("✅ Done",                           callback_data="close")],
    ])


def search_results_keyboard(results: list) -> InlineKeyboardMarkup:
    buttons = []
    for r in results:
        short = r.title[:35] + "…" if len(r.title) > 35 else r.title
        buttons.append([InlineKeyboardButton(f"📚 {short}", callback_data=f"novel|{r.url}")])
    return InlineKeyboardMarkup(buttons)
