"""Работа с базой данных SQLite для хранения настроек пользователей"""

import aiosqlite
import json
from pathlib import Path

DB_PATH = Path(__file__).parent / "data" / "bot.db"


async def init_db():
    """Инициализация базы данных"""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                enabled_topics TEXT DEFAULT '[]',
                custom_topics TEXT DEFAULT '[]',
                language_level TEXT DEFAULT 'medium',
                reading_time INTEGER DEFAULT 7,
                digest_lang TEXT DEFAULT 'ru',
                last_viewed_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        # Миграция: добавляем колонку если её нет
        try:
            await db.execute("ALTER TABLE users ADD COLUMN last_viewed_at TIMESTAMP")
        except Exception:
            pass  # Колонка уже существует
        await db.commit()


async def get_user(user_id: int) -> dict | None:
    """Получить настройки пользователя"""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)) as cursor:
            row = await cursor.fetchone()
            if row:
                return {
                    "user_id": row["user_id"],
                    "enabled_topics": json.loads(row["enabled_topics"]),
                    "custom_topics": json.loads(row["custom_topics"]),
                    "language_level": row["language_level"],
                    "reading_time": row["reading_time"],
                    "digest_lang": row["digest_lang"],
                    "last_viewed_at": row["last_viewed_at"],
                }
    return None


async def ensure_user(user_id: int) -> dict:
    """Получить или создать пользователя"""
    user = await get_user(user_id)
    if user:
        return user
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR IGNORE INTO users (user_id) VALUES (?)",
            (user_id,)
        )
        await db.commit()
    return await get_user(user_id)


async def update_enabled_topics(user_id: int, topics: list):
    """Обновить список включённых тем"""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE users SET enabled_topics = ? WHERE user_id = ?",
            (json.dumps(topics, ensure_ascii=False), user_id)
        )
        await db.commit()


async def update_custom_topics(user_id: int, topics: list):
    """Обновить кастомные темы"""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE users SET custom_topics = ? WHERE user_id = ?",
            (json.dumps(topics, ensure_ascii=False), user_id)
        )
        await db.commit()


async def update_language_level(user_id: int, level: str):
    """Обновить уровень сложности языка"""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE users SET language_level = ? WHERE user_id = ?",
            (level, user_id)
        )
        await db.commit()


async def update_reading_time(user_id: int, minutes: int):
    """Обновить время чтения"""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE users SET reading_time = ? WHERE user_id = ?",
            (minutes, user_id)
        )
        await db.commit()


async def update_digest_lang(user_id: int, lang: str):
    """Обновить язык дайджеста"""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE users SET digest_lang = ? WHERE user_id = ?",
            (lang, user_id)
        )
        await db.commit()


async def update_last_viewed(user_id: int):
    """Обновить время последнего просмотра новостей"""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE users SET last_viewed_at = CURRENT_TIMESTAMP WHERE user_id = ?",
            (user_id,)
        )
        await db.commit()


async def reset_last_viewed(user_id: int):
    """Сбросить время последнего просмотра (получать все новости)"""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE users SET last_viewed_at = NULL WHERE user_id = ?",
            (user_id,)
        )
        await db.commit()
