import asyncio
import time
import pytest

from youtube_research_mcp.services.search import SearchService
from youtube_research_mcp.services.transcripts import TranscriptService
from youtube_research_mcp.utils.single_flight import get_single_flight


@pytest.mark.asyncio
async def test_concurrency_load_and_single_flight():
    search_service = SearchService()
    flight = get_single_flight()
    initial_coalesced = flight.coalesced_count

    query = "quantum computing developments"
    concurrency_levels = [1, 10, 50, 100]

    print("\n=================================================================")
    print("      CONCURRENCY & SINGLE-FLIGHT STRESS BENCHMARK")
    print("=================================================================")

    for concurrency in concurrency_levels:
        start_t = time.perf_counter()
        tasks = [
            search_service.search(query=query, max_results=5)
            for _ in range(concurrency)
        ]
        results = await asyncio.gather(*tasks)
        elapsed_ms = (time.perf_counter() - start_t) * 1000.0

        assert len(results) == concurrency
        assert all(r.total_results > 0 for r in results)

        print(
            f"Concurrency N={concurrency:<3} | Total Time: {elapsed_ms:>6.2f}ms | Avg per Req: {elapsed_ms / concurrency:>5.2f}ms"
        )

    saved_reqs = flight.coalesced_count - initial_coalesced
    print(f"\nTotal duplicate requests coalesced by Single-Flight: {saved_reqs}")
    print("=================================================================\n")
