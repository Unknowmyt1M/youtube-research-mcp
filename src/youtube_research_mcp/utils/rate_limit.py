import asyncio
import random
import time
from typing import Optional
from youtube_research_mcp.config import settings


class AsyncTokenBucket:
    """Thread-safe and async-safe token bucket rate limiter."""

    def __init__(self, rate: float, capacity: float):
        """rate: tokens per second, capacity: maximum token burst."""
        self.rate = float(rate)
        self.capacity = float(capacity)
        self.tokens = float(capacity)
        self.last_update = time.monotonic()
        self._lock = asyncio.Lock()

    async def try_acquire(self, tokens: float = 1.0) -> bool:
        """Non-blocking token acquisition check for HTTP rate limiting."""
        async with self._lock:
            now = time.monotonic()
            elapsed = now - self.last_update
            self.last_update = now
            self.tokens = min(self.capacity, self.tokens + elapsed * self.rate)

            if self.tokens >= tokens:
                self.tokens -= tokens
                return True
            return False

    async def acquire(self, tokens: float = 1.0) -> None:
        """Blocking token acquisition with async sleep."""
        async with self._lock:
            while True:
                now = time.monotonic()
                elapsed = now - self.last_update
                self.last_update = now
                self.tokens = min(self.capacity, self.tokens + elapsed * self.rate)

                if self.tokens >= tokens:
                    self.tokens -= tokens
                    return

                needed = tokens - self.tokens
                wait_time = needed / self.rate
                await asyncio.sleep(wait_time)


class ConcurrencyLimiter:
    """Async semaphore wrapper with timeout support."""

    def __init__(self, max_concurrent: int):
        self.semaphore = asyncio.Semaphore(max_concurrent)

    async def run(self, coro):
        async with self.semaphore:
            return await coro


async def backoff_retry(
    coro_func,
    max_retries: int = 3,
    base_delay: float = 0.5,
    max_delay: float = 5.0,
    retry_exceptions: tuple = (Exception,),
):
    """Execute async callable with full jitter exponential backoff."""
    attempt = 0
    while True:
        try:
            return await coro_func()
        except retry_exceptions as e:
            attempt += 1
            if attempt > max_retries:
                raise e
            sleep_cap = min(max_delay, base_delay * (2 ** (attempt - 1)))
            sleep_time = random.uniform(base_delay, sleep_cap)
            await asyncio.sleep(sleep_time)


_global_rate_limiter: Optional[AsyncTokenBucket] = None


def get_rate_limiter() -> AsyncTokenBucket:
    """Return the global rate limiter singleton configured by settings."""
    global _global_rate_limiter
    if _global_rate_limiter is None:
        _global_rate_limiter = AsyncTokenBucket(
            rate=settings.RATE_LIMIT_RPS,
            capacity=settings.RATE_LIMIT_BURST,
        )
    return _global_rate_limiter
