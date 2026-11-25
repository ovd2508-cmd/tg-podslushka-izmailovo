import aiosqlite

DB_PATH = "bot.db"


async def init_db() -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS admin_messages (
                admin_message_id INTEGER PRIMARY KEY,
                user_id INTEGER NOT NULL
            )
            """
        )
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS user_cooldowns (
                user_id INTEGER PRIMARY KEY,
                last_sent_at REAL NOT NULL
            )
            """
        )
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS user_stats (
                user_id INTEGER PRIMARY KEY,
                suggestions_count INTEGER NOT NULL DEFAULT 0
            )
            """
        )
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS user_profiles (
                user_id INTEGER PRIMARY KEY,
                display_name TEXT,
                is_anonymous INTEGER NOT NULL DEFAULT 0,
                updated_at REAL NOT NULL
            )
            """
        )
        await db.commit()


async def save_admin_message(admin_message_id: int, user_id: int) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR REPLACE INTO admin_messages (admin_message_id, user_id) VALUES (?, ?)",
            (admin_message_id, user_id),
        )
        await db.commit()


async def get_user_id_by_admin_message(admin_message_id: int) -> int | None:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT user_id FROM admin_messages WHERE admin_message_id = ?",
            (admin_message_id,),
        ) as cursor:
            row = await cursor.fetchone()
            return row[0] if row else None


async def get_last_sent_at(user_id: int) -> float | None:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT last_sent_at FROM user_cooldowns WHERE user_id = ?",
            (user_id,),
        ) as cursor:
            row = await cursor.fetchone()
            return row[0] if row else None


async def update_cooldown(user_id: int, timestamp: float) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR REPLACE INTO user_cooldowns (user_id, last_sent_at) VALUES (?, ?)",
            (user_id, timestamp),
        )
        await db.commit()


# ---------- Новые функции для статистики и профилей ----------


async def increment_suggestion_count(user_id: int) -> None:
    """Инкрементировать счётчик предложений пользователя."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """
            INSERT INTO user_stats (user_id, suggestions_count) VALUES (?, 1)
            ON CONFLICT(user_id) DO UPDATE SET suggestions_count = suggestions_count + 1
            """,
            (user_id,),
        )
        await db.commit()


async def get_top_users(limit: int = 10) -> list[dict]:
    """Вернуть топ пользователей по количеству предложений."""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            """
            SELECT us.user_id, us.suggestions_count, up.display_name, up.is_anonymous
            FROM user_stats us
            LEFT JOIN user_profiles up ON us.user_id = up.user_id
            ORDER BY us.suggestions_count DESC
            LIMIT ?
            """,
            (limit,),
        ) as cursor:
            rows = await cursor.fetchall()
            return [
                {
                    "user_id": row[0],
                    "suggestions_count": row[1],
                    "display_name": row[2],
                    "is_anonymous": bool(row[3]),
                }
                for row in rows
            ]


async def save_user_profile(
    user_id: int,
    display_name: str | None,
    is_anonymous: bool,
) -> None:
    """Сохранить или обновить профиль пользователя (никнейм / анонимность)."""
    from datetime import datetime, timezone

    updated_at = datetime.now(timezone.utc).timestamp()
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """
            INSERT INTO user_profiles (user_id, display_name, is_anonymous, updated_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                display_name = excluded.display_name,
                is_anonymous = excluded.is_anonymous,
                updated_at = excluded.updated_at
            """,
            (user_id, display_name, int(is_anonymous), updated_at),
        )
        await db.commit()


async def get_user_profile(user_id: int) -> dict | None:
    """Получить профиль пользователя."""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            """
            SELECT display_name, is_anonymous
            FROM user_profiles WHERE user_id = ?
            """,
            (user_id,),
        ) as cursor:
            row = await cursor.fetchone()
            if not row:
                return None
            return {
                "user_id": user_id,
                "display_name": row[0],
                "is_anonymous": bool(row[1]),
            }