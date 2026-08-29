import asyncio
from typing import Any, Callable, Coroutine, Dict, Optional, TypeVar

T = TypeVar("T")


class SingleFlight:
    """Async single-flight / request coalescer to prevent cache stampedes.

    When multiple concurrent coroutines request the same key simultaneously,
    only one coroutine executes the underlying function, and all other callers
    await the exact same shared result.
    """

    def __init__(self):
        self._lock = asyncio.Lock()
        self._in_flight: Dict[str, asyncio.Future] = {}
        self._coalesced_count: int = 0

    @property
    def coalesced_count(self) -> int:
        """Total number of duplicate requests that were coalesced into existing flights."""
        return self._coalesced_count

    async def execute(
        self, key: str, coro_fn: Callable[[], Coroutine[Any, Any, T]]
    ) -> T:
        """Execute coro_fn if key is not currently in flight, otherwise await the in-flight future."""
        fut: Optional[asyncio.Future] = None
        is_leader = False

        async with self._lock:
            if key in self._in_flight:
                self._coalesced_count += 1
                try:
                    from youtube_research_mcp.utils.metrics import metrics
                    metrics.record_coalesced_request()
                except Exception:
                    pass
                fut = self._in_flight[key]
            else:
                loop = asyncio.get_running_loop()
                fut = loop.create_future()
                self._in_flight[key] = fut
                is_leader = True

        if not is_leader:
            # Await leader's execution
            return await asyncio.shield(fut)

        # We are the leader: run the actual operation
        try:
            result = await coro_fn()
            fut.set_result(result)
            return result
        except BaseException as e:
            fut.set_exception(e)
            raise e
        finally:
            async with self._lock:
                self._in_flight.pop(key, None)


# Global singleton
_global_single_flight = SingleFlight()


def get_single_flight() -> SingleFlight:
    return _global_single_flight
