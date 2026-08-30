import asyncio
import time
import pytest
from youtube_research_mcp.utils.single_flight import SingleFlight


@pytest.mark.asyncio
async def test_single_flight_100_concurrent_identical_requests():
    """Verify 100 concurrent callers for same key execute upstream once and 99 coalesce."""
    sf = SingleFlight()
    upstream_executions = 0

    async def slow_upstream():
        nonlocal upstream_executions
        upstream_executions += 1
        await asyncio.sleep(0.05)
        return {"data": "verified_result", "timestamp": time.time()}

    tasks = [sf.execute("flight_100_test", slow_upstream) for _ in range(100)]
    results = await asyncio.gather(*tasks)

    assert upstream_executions == 1
    assert sf.coalesced_count == 99
    assert len(results) == 100
    first_res = results[0]
    for r in results:
        assert r == first_res


@pytest.mark.asyncio
async def test_single_flight_different_keys_are_independent():
    """Verify distinct flight keys run independently without coalescing."""
    sf = SingleFlight()
    exec_map = {"key_a": 0, "key_b": 0, "key_c": 0}

    async def make_task(k):
        async def work():
            exec_map[k] += 1
            await asyncio.sleep(0.02)
            return f"result_{k}"
        return await sf.execute(k, work)

    results = await asyncio.gather(
        make_task("key_a"),
        make_task("key_a"),
        make_task("key_b"),
        make_task("key_c"),
        make_task("key_c"),
    )

    assert exec_map["key_a"] == 1
    assert exec_map["key_b"] == 1
    assert exec_map["key_c"] == 1
    assert sf.coalesced_count == 2  # 1 for key_a, 1 for key_c
    assert results[0] == "result_key_a"
    assert results[1] == "result_key_a"
    assert results[2] == "result_key_b"
    assert results[3] == "result_key_c"
    assert results[4] == "result_key_c"


@pytest.mark.asyncio
async def test_single_flight_failure_propagation_and_cleanup():
    """Verify upstream failure propagates to all waiters and key is cleaned up for retry."""
    sf = SingleFlight()
    upstream_calls = 0

    async def failing_upstream():
        nonlocal upstream_calls
        upstream_calls += 1
        await asyncio.sleep(0.02)
        raise RuntimeError("Upstream API 500 error")

    tasks = [sf.execute("failing_key", failing_upstream) for _ in range(10)]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    assert upstream_calls == 1
    assert len(results) == 10
    for r in results:
        assert isinstance(r, RuntimeError)
        assert "Upstream API 500 error" in str(r)

    # Verify flight key is cleaned up and subsequent requests can retry
    async def successful_retry():
        return "success_after_retry"

    retry_res = await sf.execute("failing_key", successful_retry)
    assert retry_res == "success_after_retry"


@pytest.mark.asyncio
async def test_single_flight_waiter_cancellation_does_not_break_leader():
    """Verify cancelling one waiting task does not cancel the leader or corrupt results for other waiters."""
    sf = SingleFlight()
    upstream_finished = False

    async def long_upstream():
        nonlocal upstream_finished
        await asyncio.sleep(0.1)
        upstream_finished = True
        return "leader_completed"

    task1 = asyncio.create_task(sf.execute("cancel_key", long_upstream))
    task2 = asyncio.create_task(sf.execute("cancel_key", long_upstream))
    task3 = asyncio.create_task(sf.execute("cancel_key", long_upstream))

    await asyncio.sleep(0.01)
    # Cancel task2
    task2.cancel()

    with pytest.raises(asyncio.CancelledError):
        await task2

    # task1 and task3 must still succeed
    res1 = await task1
    res3 = await task3
    assert res1 == "leader_completed"
    assert res3 == "leader_completed"
    assert upstream_finished is True
