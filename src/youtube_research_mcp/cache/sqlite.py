import json
import os
import time
from pathlib import Path
from typing import Any, Optional
import aiosqlite

from youtube_research_mcp.cache.base import BaseCache


class SQLiteCache(BaseCache):
    """High-performance SQLite cache with WAL mode, memory-mapped I/O, and automated TTL."""

    def __init__(self, db_path: str):
        self.db_path = Path(os.path.expanduser(db_path))
        self._db: Optional[aiosqlite.Connection] = None
        self._initialized = False

    async def _ensure_db(self) -> aiosqlite.Connection:
        if self._db is None or not self._initialized:
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
            self._db = await aiosqlite.connect(str(self.db_path))

            # Optimize SQLite PRAGMAs for high throughput and concurrency
            await self._db.execute("PRAGMA journal_mode = WAL;")
            await self._db.execute("PRAGMA synchronous = NORMAL;")
            await self._db.execute("PRAGMA cache_size = -32000;")  # 32MB cache
            await self._db.execute("PRAGMA temp_store = MEMORY;")
            await self._db.execute("PRAGMA mmap_size = 268435456;")  # 256MB MMAP
            await self._db.execute("PRAGMA busy_timeout = 5000;")

            # Cache key-value table
            await self._db.execute(
                """
                CREATE TABLE IF NOT EXISTS cache_store (
                    key TEXT PRIMARY KEY,
                    value_json TEXT NOT NULL,
                    category TEXT DEFAULT 'general',
                    created_at INTEGER NOT NULL,
                    expires_at INTEGER NOT NULL
                )
                """
            )
            await self._db.execute(
                "CREATE INDEX IF NOT EXISTS idx_cache_expires ON cache_store(expires_at)"
            )
            await self._db.execute(
                "CREATE INDEX IF NOT EXISTS idx_cache_category ON cache_store(category)"
            )
            await self._db.commit()
            self._initialized = True

        return self._db

    async def get(self, key: str) -> Optional[Any]:
        db = await self._ensure_db()
        now = int(time.time())
        async with db.execute(
            "SELECT value_json FROM cache_store WHERE key = ? AND expires_at > ?",
            (key, now),
        ) as cursor:
            row = await cursor.fetchone()
            if row:
                try:
                    return json.loads(row[0])
                except Exception:
                    return None
        return None

    async def set(
        self, key: str, value: Any, ttl_seconds: int, category: str = "general"
    ) -> None:
        db = await self._ensure_db()
        now = int(time.time())
        expires_at = now + ttl_seconds
        value_json = json.dumps(value)

        await db.execute(
            """
            INSERT INTO cache_store (key, value_json, category, created_at, expires_at)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(key) DO UPDATE SET
                value_json = excluded.value_json,
                category = excluded.category,
                created_at = excluded.created_at,
                expires_at = excluded.expires_at
            """,
            (key, value_json, category, now, expires_at),
        )
        await db.commit()

    async def delete(self, key: str) -> bool:
        db = await self._ensure_db()
        cursor = await db.execute("DELETE FROM cache_store WHERE key = ?", (key,))
        await db.commit()
        return cursor.rowcount > 0

    async def clear_expired(self) -> int:
        db = await self._ensure_db()
        now = int(time.time())
        cursor = await db.execute(
            "DELETE FROM cache_store WHERE expires_at <= ?", (now,)
        )
        await db.commit()
        return cursor.rowcount

    async def close(self) -> None:
        if self._db:
            await self._db.close()
            self._db = None
            self._initialized = False
