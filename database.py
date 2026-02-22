import motor.motor_asyncio
from datetime import datetime, date
from config import Config

client = motor.motor_asyncio.AsyncIOMotorClient(Config.MONGODB_URI)
db     = client["NovelScraper"]

users_col    = db["users"]
stats_col    = db["stats"]
novels_col   = db["novels"]

# ─── Default user document ────────────────────────────────────────────────────
def _default_user(user_id: int, first_name: str = "") -> dict:
    return {
        "_id":            user_id,
        "first_name":     first_name,
        "joined":         datetime.utcnow(),
        "last_seen":      datetime.utcnow(),
        "last_novel_url": None,
        "last_chapter":   0,
        "chapters_read":  0,
        "settings": {
            "reading_mode":       "telegram",   # "telegram" | "file"
            "auto_next":          True,
            "send_cover":         True,
            "download_buttons":   True,
        },
    }

# ─── User helpers ─────────────────────────────────────────────────────────────
async def add_user(user_id: int, first_name: str = ""):
    if not await users_col.find_one({"_id": user_id}):
        await users_col.insert_one(_default_user(user_id, first_name))
        await _increment_stat("total_users")
    else:
        await users_col.update_one(
            {"_id": user_id},
            {"$set": {"last_seen": datetime.utcnow(), "first_name": first_name}},
        )

async def get_user(user_id: int) -> dict | None:
    return await users_col.find_one({"_id": user_id})

async def update_user(user_id: int, data: dict):
    await users_col.update_one({"_id": user_id}, {"$set": data}, upsert=True)

async def get_all_users():
    return users_col.find({})

async def total_users() -> int:
    return await users_col.count_documents({})

async def active_today() -> int:
    today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    return await users_col.count_documents({"last_seen": {"$gte": today}})

# ─── Settings helpers ─────────────────────────────────────────────────────────
async def get_settings(user_id: int) -> dict:
    user = await get_user(user_id)
    if user and "settings" in user:
        return user["settings"]
    return _default_user(user_id)["settings"]

async def update_setting(user_id: int, key: str, value):
    await users_col.update_one(
        {"_id": user_id},
        {"$set": {f"settings.{key}": value}},
        upsert=True,
    )

# ─── Stats helpers ────────────────────────────────────────────────────────────
async def _increment_stat(key: str, amount: int = 1):
    await stats_col.update_one(
        {"_id": "global"},
        {"$inc": {key: amount}},
        upsert=True,
    )

async def increment_chapters_sent(amount: int = 1):
    await _increment_stat("chapters_sent", amount)

async def increment_novels_scraped():
    await _increment_stat("novels_scraped")

async def get_stats() -> dict:
    doc = await stats_col.find_one({"_id": "global"}) or {}
    return {
        "total_users": await total_users(),
        "active":      await active_today(),
        "novels":      doc.get("novels_scraped", 0),
        "chapters":    doc.get("chapters_sent", 0),
    }

# ─── Reading progress ─────────────────────────────────────────────────────────
async def save_progress(user_id: int, novel_url: str, chapter_index: int):
    await update_user(user_id, {
        "last_novel_url": novel_url,
        "last_chapter":   chapter_index,
    })

async def get_progress(user_id: int) -> tuple[str | None, int]:
    user = await get_user(user_id)
    if not user:
        return None, 0
    return user.get("last_novel_url"), user.get("last_chapter", 0)
