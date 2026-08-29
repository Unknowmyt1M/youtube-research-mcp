import asyncio
import pytest
from youtube_research_mcp.utils.single_flight import SingleFlight


@pytest.mark.asyncio
async def test_single_flight_coalescing():
    sf = SingleFlight()
    call_count = 0

    async def slow_work():
        nonlocal call_count
        call_count += 1
        await asyncio.sleep(0.05)
        return "shared_result"

    # Launch 10 concurrent requests for the exact same key
    tasks = [sf.execute("flight_key_1", slow_work) for _ in range(10)]
    results = await asyncio.gather(*tasks)

    # All 10 callers must receive the exact same result
    assert all(r == "shared_result" for r in results)
    # The slow_work function must have only executed ONCE!
    assert call_count == 1
    # 9 requests were saved/coalesced
    assert sf.coalesced_count == 9


@pytest.mark.asyncio
async def test_single_flight_different_keys_are_concurrent():
    sf = SingleFlight()
    call_counts = {"keyA": 0, "keyB": 0}

    async def work_a():
        call_counts["keyA"] += 1
        await asyncio.sleep(0.02)
        return "resA"

    async def work_b():
        call_counts["keyB"] += 1
        await asyncio.sleep(0.02)
        return "resB"

    res_a, res_b = await asyncio.gather(
        sf.execute("keyA", work_a),
        sf.execute("keyB", work_b),
    )

    assert res_a == "resA"
    assert res_b == "resB"
    assert call_counts["keyA"] == 1
    assert call_counts["keyB"] == 1


@pytest.mark.asyncio
async def test_single_flight_exception_propagation():
    sf = SingleFlight()

    async def failing_work():
        await asyncio.sleep(0.02)
        raise ValueError("Upstream failure")

    tasks = [sf.execute("fail_key", failing_work) for _ in range(5)]

    results = await asyncio.gather(*tasks, return_exceptions=True)
    assert len(results) == 5
    for r in results:
        assert isinstance(r, ValueError)
        assert str(r) == "Upstream failure"
