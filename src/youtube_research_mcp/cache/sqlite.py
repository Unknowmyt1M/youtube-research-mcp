import asyncio
import json
from pathlib import Path
import time
from typing import Any, Optional, Tuple
import aiosqlite

from youtube_research_mcp.cache.base import BaseCache
from youtube_research_mcp.config import settings


class SQLiteCache(BaseCache):
    """High-performance SQLite cache with WAL mode, versioning, and negative caching."""

    NEGATIVE_FLAG = "__negative__"

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or settings.CACHE_DB_PATH
        self._init_lock = asyncio.Lock()
        self._initialized = False

    async def _ensure_db(self):
        if self._initialized:
            return

        async with self._init_lock:
            if self._initialized:
                return

            p = Path(self.db_path)
            p.parent.mkdir(parents=True, exist_ok=True)

            async with aiosqlite.connect(self.db_path) as db:
                await db.execute("PRAGMA journal_mode = WAL;")
                await db.execute("PRAGMA synchronous = NORMAL;")
                await db.execute("PRAGMA mmap_size = 268435456;")  # 256MB
                await db.execute("PRAGMA cache_size = -64000;")  # 64MB RAM

                # Check if old table or schema without 'value' column exists
                async with db.execute("PRAGMA table_info(cache_store);") as cursor:
                    cols = [row[1] for row in await cursor.fetchall()]

                if cols and "value" not in cols:
                    await db.execute("DROP TABLE IF EXISTS cache_store;")

                await db.execute("DROP TABLE IF EXISTS cache_entries;")

                # Ensure cache_store has the required columns
                await db.execute(
                    """
                    CREATE TABLE IF NOT EXISTS cache_store (
                        key TEXT PRIMARY KEY,
                        value TEXT NOT NULL,
                        is_negative INTEGER DEFAULT 0,
                        created_at REAL NOT NULL,
                        expires_at REAL NOT NULL
                    );
                    """
                )
                await db.execute(
                    "CREATE INDEX IF NOT EXISTS idx_expires_at ON cache_store(expires_at);"
                )
                await db.commit()

            self._initialized = True

    async def get(self, key: str) -> Optional[Any]:
        val, is_neg = await self.get_with_status(key)
        if is_neg:
            return None
        return val

    async def get_with_status(self, key: str) -> Tuple[Optional[Any], bool]:
        await self._ensure_db()
        v_key = self.format_key(key)
        now = time.time()

        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(
                "SELECT value, is_negative, expires_at FROM cache_store WHERE key = ?;",
                (v_key,),
            ) as cursor:
                row = await cursor.fetchone()
                if not row:
                    return None, False

                raw_val, is_neg, expires_at = row
                if expires_at <= now:
                    # Expired
                    await db.execute(
                        "DELETE FROM cache_store WHERE key = ?;", (v_key,)
                    )
                    await db.commit()
                    return None, False

                try:
                    data = json.loads(raw_val)
                    return data, bool(is_neg)
                except Exception:
                    return None, False

    async def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None,
        ttl_seconds: Optional[int] = None,
    ) -> None:
        await self._ensure_db()
        v_key = self.format_key(key)
        now = time.time()
        effective_ttl = ttl if ttl is not None else (ttl_seconds if ttl_seconds is not None else settings.CACHE_TTL_METADATA)
        expires_at = now + effective_ttl
        raw_val = json.dumps(value)

    async def _prune_if_needed(self, db: aiosqlite.Connection, now: float) -> None:
        """Prune cache entries if table count reaches MAX_CACHE_ENTRIES, prioritizing expired keys."""
        prefix_pattern = f"{settings.CACHE_SCHEMA_VERSION}:%"
        async with db.execute(
            "SELECT COUNT(*) FROM cache_store WHERE key LIKE ?;", (prefix_pattern,)
        ) as cursor:
            count_row = await cursor.fetchone()
            current_count = count_row[0] if count_row else 0

        if current_count >= settings.MAX_CACHE_ENTRIES:
            # 1. Delete expired keys in current version namespace first
            await db.execute(
                "DELETE FROM cache_store WHERE key LIKE ? AND expires_at <= ?;",
                (prefix_pattern, now),
            )
            # 2. Re-check count; if still over limit, delete oldest expiring keys
            async with db.execute(
                "SELECT COUNT(*) FROM cache_store WHERE key LIKE ?;", (prefix_pattern,)
            ) as cursor:
                count_row2 = await cursor.fetchone()
                current_count2 = count_row2[0] if count_row2 else 0

            if current_count2 >= settings.MAX_CACHE_ENTRIES:
                await db.execute(
                    """
                    DELETE FROM cache_store
                    WHERE key IN (
                        SELECT key FROM cache_store
                        WHERE key LIKE ?
                        ORDER BY expires_at ASC
                        LIMIT 50
                    );
                    """,
                    (prefix_pattern,),
                )

    async def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None,
        ttl_seconds: Optional[int] = None,
    ) -> None:
        await self._ensure_db()
        v_key = self.format_key(key)
        now = time.time()
        effective_ttl = ttl if ttl is not None else (ttl_seconds if ttl_seconds is not None else settings.CACHE_TTL_METADATA)
        expires_at = now + effective_ttl
        raw_val = json.dumps(value)

        async with aiosqlite.connect(self.db_path) as db:
            await self._prune_if_needed(db, now)
            await db.execute(
                """
                INSERT OR REPLACE INTO cache_store (key, value, is_negative, created_at, expires_at)
                VALUES (?, ?, 0, ?, ?);
                """,
                (v_key, raw_val, now, expires_at),
            )
            await db.commit()

    async def set_negative(
        self,
        key: str,
        reason: str,
        ttl: Optional[int] = None,
        ttl_seconds: Optional[int] = None,
    ) -> None:
        await self._ensure_db()
        v_key = self.format_key(key)
        now = time.time()
        effective_ttl = ttl if ttl is not None else (ttl_seconds if ttl_seconds is not None else settings.NEGATIVE_CACHE_TTL)
        expires_at = now + effective_ttl
        raw_val = json.dumps({self.NEGATIVE_FLAG: True, "reason": reason})

        async with aiosqlite.connect(self.db_path) as db:
            await self._prune_if_needed(db, now)
            await db.execute(
                """
                INSERT OR REPLACE INTO cache_store (key, value, is_negative, created_at, expires_at)
                VALUES (?, ?, 1, ?, ?);
                """,
                (v_key, raw_val, now, expires_at),
            )
            await db.commit()

    async def delete(self, key: str) -> bool:
        await self._ensure_db()
        v_key = self.format_key(key)
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "DELETE FROM cache_store WHERE key = ?;", (v_key,)
            )
            await db.commit()
            return cursor.rowcount > 0

    async def clear(self) -> None:
        await self._ensure_db()
        prefix_pattern = f"{settings.CACHE_SCHEMA_VERSION}:%"
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("DELETE FROM cache_store WHERE key LIKE ?;", (prefix_pattern,))
            await db.commit()

    async def purge_expired(self) -> int:
        await self._ensure_db()
        now = time.time()
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "DELETE FROM cache_store WHERE expires_at <= ?;", (now,)
            )
            count = cursor.rowcount
            await db.commit()
            await db.execute("PRAGMA wal_checkpoint(PASSIVE);")
            return max(0, count)

    async def close(self) -> None:
        pass
