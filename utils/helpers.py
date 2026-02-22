import logging
import time
from typing import Optional

import aiohttp
from pyrogram.types import Message

from config import Config
from script import script

logger = logging.getLogger(__name__)


def make_progress_bar(done: int, total: int, width: int = 20) -> str:
    filled = int(width * done / total) if total else 0
    return "█" * filled + "░" * (width - filled)


async def edit_progress(msg: Message, done: int, total: int, start_ts: float):
    pct     = int(done * 100 / total) if total else 0
    elapsed = time.time() - start_ts
    eta_sec = int((elapsed / done) * (total - done)) if done else 0
    eta_str = f"{eta_sec//60}m {eta_sec%60}s" if eta_sec >= 60 else f"{eta_sec}s"
    bar     = make_progress_bar(done, total)
    text    = script.DOWNLOAD_PROGRESS.format(
        bar=bar, done=done, total=total, pct=pct, eta=eta_str
    )
    try:
        await msg.edit_text(text)
    except Exception:
        pass


async def fetch_random_wallpaper() -> Optional[str]:
    try:
        async with aiohttp.ClientSession() as s:
            async with s.get(Config.WALLPAPER_API, timeout=aiohttp.ClientTimeout(total=10)) as r:
                if r.status == 200:
                    data = await r.json(content_type=None)
                    return data.get("url") or data.get("image") or str(r.url)
    except Exception as e:
        logger.warning(f"Wallpaper fetch failed: {e}")
    return None


def split_text(text: str, limit: int = 4000) -> list[str]:
    parts = []
    while len(text) > limit:
        cut = text.rfind("\n\n", 0, limit)
        if cut == -1:
            cut = limit
        parts.append(text[:cut])
        text = text[cut:].lstrip()
    if text:
        parts.append(text)
    return parts
