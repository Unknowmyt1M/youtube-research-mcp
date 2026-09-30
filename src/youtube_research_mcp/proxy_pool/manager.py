import asyncio
import json
import logging
import os
import time
from typing import Dict, List, Optional

from youtube_research_mcp.proxy_pool.config import config
from youtube_research_mcp.proxy_pool.fetcher import ProxyFetcher
from youtube_research_mcp.proxy_pool.validator import ProxyValidator

logger = logging.getLogger(__name__)


class ProxyPoolManager:
    """Async-native singleton manager for self-healing, auto-refreshing YouTube proxy pool."""

    def __init__(self):
        self._pool: List[dict] = []
        self._index: int = 0
        self._lock = asyncio.Lock()
        self._bg_task: Optional[asyncio.Task] = None
        self._is_running: bool = False
        self._stats = {
            "total_requests": 0,
            "successes": 0,
            "failures": 0,
            "last_refresh_time": 0.0,
        }
        # Load cached proxies on init for instant zero-wait startup
        self._load_from_cache()

    def _load_from_cache(self):
        """Load previously verified proxies from disk cache."""
        try:
            if os.path.exists(config.CACHE_FILE_PATH):
                with open(config.CACHE_FILE_PATH, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, list) and len(data) > 0:
                        self._pool = data
                        logger.info(f"Loaded {len(self._pool)} working proxies from disk cache '{config.CACHE_FILE_PATH}'.")
        except Exception as e:
            logger.debug(f"Could not load proxy pool cache: {e}")

    def _save_to_cache(self):
        """Save verified proxies to disk cache for subsequent cold starts."""
        try:
            with open(config.CACHE_FILE_PATH, "w", encoding="utf-8") as f:
                json.dump(self._pool, f, indent=2)
        except Exception as e:
            logger.debug(f"Could not save proxy pool cache: {e}")

    @property
    def pool_size(self) -> int:
        return len(self._pool)

    @property
    def is_empty(self) -> bool:
        return len(self._pool) == 0

    async def get_proxy(self) -> Optional[str]:
        """Retrieve the next healthy proxy via round-robin."""
        if not config.ENABLED:
            return None

        async with self._lock:
            if not self._pool:
                return None
            self._stats["total_requests"] += 1
            entry = self._pool[self._index % len(self._pool)]
            self._index = (self._index + 1) % len(self._pool)
            return entry["proxy"]

    async def report_success(self, proxy_url: str):
        """Record successful request through proxy."""
        async with self._lock:
            self._stats["successes"] += 1
            for p in self._pool:
                if p["proxy"] == proxy_url:
                    p["consecutive_failures"] = 0
                    break

    async def report_failure(self, proxy_url: str):
        """Record failed request. Auto-evicts proxy if threshold exceeded."""
        async with self._lock:
            self._stats["failures"] += 1
            for i, p in enumerate(self._pool):
                if p["proxy"] == proxy_url:
                    p["consecutive_failures"] = p.get("consecutive_failures", 0) + 1
                    if p["consecutive_failures"] >= config.MAX_CONSECUTIVE_FAILURES:
                        logger.warning(f"Evicting dead proxy '{proxy_url}' from active pool ({p['consecutive_failures']} consecutive fails).")
                        self._pool.pop(i)
                        self._save_to_cache()
                    break

    async def refresh_pool(self) -> int:
        """Trigger a full fetch + validate + update cycle."""
        logger.info("Starting background proxy pool refresh cycle...")
        start_t = time.time()
        
        # 1. Fetch candidates from all sources
        candidates = await ProxyFetcher.fetch_all()
        if not candidates:
            logger.warning("No candidate proxies discovered from public sources.")
            return len(self._pool)

        # 2. Parallel validation directly against YouTube
        verified = await ProxyValidator.validate_pool(candidates)

        async with self._lock:
            if verified:
                self._pool = verified
                self._index = 0
                self._stats["last_refresh_time"] = time.time()
                self._save_to_cache()
                logger.info(f"Proxy pool refreshed: {len(self._pool)} active verified proxies ready (took {round(time.time() - start_t, 1)}s).")
            else:
                logger.warning("Validation completed with 0 working YouTube proxies. Keeping existing pool.")

        return len(self._pool)

    async def start_background_refresher(self):
        """Start non-blocking periodic background refresh worker."""
        if not config.ENABLED or self._is_running:
            return

        self._is_running = True

        async def _refresher_loop():
            logger.info(f"ProxyPool background refresher daemon started (sync interval: {config.REFRESH_INTERVAL_SECONDS}s).")
            # If pool is empty on start, trigger initial refresh immediately
            if not self._pool:
                try:
                    await self.refresh_pool()
                except Exception as e:
                    logger.error(f"Initial proxy refresh error: {e}")

            while self._is_running:
                try:
                    await asyncio.sleep(config.REFRESH_INTERVAL_SECONDS)
                    if self._is_running:
                        await self.refresh_pool()
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    logger.error(f"Error in proxy pool refresher loop: {e}")

        self._bg_task = asyncio.create_task(_refresher_loop())

    async def stop(self):
        """Stop background worker gracefully."""
        self._is_running = False
        if self._bg_task:
            self._bg_task.cancel()
            try:
                await self._bg_task
            except asyncio.CancelledError:
                pass
            self._bg_task = None
        logger.info("ProxyPool background refresher stopped.")

    def get_stats(self) -> Dict[str, any]:
        """Return operational statistics for monitoring/CLI."""
        return {
            "enabled": config.ENABLED,
            "active_proxies_count": len(self._pool),
            "stats": dict(self._stats),
            "top_proxies": [
                {"proxy": p["proxy"], "latency_ms": int(p["latency"] * 1000)}
                for p in self._pool[:5]
            ],
        }


# Global singleton instance
_proxy_pool_manager: Optional[ProxyPoolManager] = None


def get_proxy_pool_manager() -> ProxyPoolManager:
    global _proxy_pool_manager
    if _proxy_pool_manager is None:
        _proxy_pool_manager = ProxyPoolManager()
    return _proxy_pool_manager
