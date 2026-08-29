import asyncio
import pytest
from youtube_research_mcp.utils.metrics import metrics
from youtube_research_mcp.utils.single_flight import SingleFlight


@pytest.mark.asyncio
async def test_single_flight_updates_metrics():
    """Verify that N concurrent identical requests execute 1 upstream call and update metrics correctly."""
    sf = SingleFlight()
    execution_count = 0
    initial_metric_val = metrics.single_flight_coalesced

    async def slow_operation():
        nonlocal execution_count
        execution_count += 1
        await asyncio.sleep(0.05)
        return "shared_value"

    # Launch 5 concurrent calls
    tasks = [sf.execute("flight_metric_test_key", slow_operation) for _ in range(5)]
    results = await asyncio.gather(*tasks)

    # 1 execution, 4 coalesced
    assert execution_count == 1
    assert all(r == "shared_value" for r in results)
    assert sf.coalesced_count == 4
    assert metrics.single_flight_coalesced >= initial_metric_val + 4
