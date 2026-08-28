import asyncio
import random
import time
from typing import Optional


class AsyncTokenBucket:
    """Thread-safe and async-safe token bucket rate limiter."""

    def __init__(self, rate: float, capacity: float):
        """rate: tokens per second, capacity: maximum token burst."""
        self.rate = rate
        self.capacity = capacity
        self.tokens = capacity
        self.last_update = time.monotonic()
        self._lock = asyncio.Lock()

    async def acquire(self, tokens: float = 1.0) -> None:
        async with self._lock:
            while True:
                now = time.monotonic()
                elapsed = now - self.last_update
                self.last_update = now
                self.tokens = min(self.capacity, self.tokens + elapsed * self.rate)

                if self.tokens >= tokens:
                    self.tokens -= tokens
                    return

                # Calculate wait time needed for next token
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
            # Full jitter formula: sleep = uniform(0, min(max_delay, base_delay * 2^attempt))
            sleep_cap = min(max_delay, base_delay * (2 ** (attempt - 1)))
            sleep_time = random.uniform(base_delay, sleep_cap)
            await asyncio.sleep(sleep_time)
