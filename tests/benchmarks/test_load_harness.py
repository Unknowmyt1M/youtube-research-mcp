import asyncio
import json
import os
import sys
import time
from typing import Any, Dict, List
import numpy as np
import pytest

from youtube_research_mcp.cache.memory import MemoryCache
from youtube_research_mcp.models.transcript import TranscriptChunk
from youtube_research_mcp.services.retrieval import HybridRetrievalIndex
from youtube_research_mcp.utils.single_flight import SingleFlight


async def run_concurrent_load_test(
    concurrency: int,
    workload_type: str,  # "cached" or "fresh"
) -> Dict[str, Any]:
    latencies: List[float] = []
    errors: int = 0
    coalesced_count: int = 0

    if workload_type == "cached":
        cache = MemoryCache()
        # Seed cache
        await cache.set("load_test_key", {"data": "cached_payload", "status": "ok"}, ttl_seconds=600)

        async def _worker():
            t0 = time.perf_counter()
            try:
                res = await cache.get("load_test_key")
                assert res is not None
            except Exception:
                nonlocal errors
                errors += 1
            finally:
                latencies.append((time.perf_counter() - t0) * 1000.0)

        start_time = time.perf_counter()
        await asyncio.gather(*[_worker() for _ in range(concurrency)])
        total_time = time.perf_counter() - start_time

    else:  # "fresh" with single-flight
        sf = SingleFlight()
        dummy_chunks = [
            TranscriptChunk(
                video_id="load_vid",
                chunk_id=i,
                start_seconds=float(i * 10),
                end_seconds=float((i + 1) * 10),
                time_range=f"00:{i*10:02d} - 00:{(i+1)*10:02d}",
                text=f"This is transcript segment {i} discussing software architecture and reliability.",
                word_count=10,
                url=f"https://www.youtube.com/watch?v=load_vid&t={i*10}s",
            )
            for i in range(10)
        ]
        index = HybridRetrievalIndex(dummy_chunks)

        async def _worker():
            t0 = time.perf_counter()
            try:
                async def _retrieve():
                    # in-process retrieval search
                    await asyncio.sleep(0.01)
                    return index.search("software architecture reliability", top_k=3)

                res = await sf.execute("fresh_query_key", _retrieve)
                assert len(res) > 0
            except Exception:
                nonlocal errors
                errors += 1
            finally:
                latencies.append((time.perf_counter() - t0) * 1000.0)

        start_time = time.perf_counter()
        await asyncio.gather(*[_worker() for _ in range(concurrency)])
        total_time = time.perf_counter() - start_time
        coalesced_count = sf.coalesced_count

    lat_arr = np.array(latencies, dtype=np.float64)
    p50 = float(np.percentile(lat_arr, 50))
    p95 = float(np.percentile(lat_arr, 95))
    p99 = float(np.percentile(lat_arr, 99))
    throughput = round(concurrency / max(total_time, 1e-6), 2)

    return {
        "concurrency": concurrency,
        "workload_type": workload_type,
        "total_requests": concurrency,
        "total_time_seconds": round(total_time, 4),
        "throughput_req_sec": throughput,
        "p50_latency_ms": round(p50, 3),
        "p95_latency_ms": round(p95, 3),
        "p99_latency_ms": round(p99, 3),
        "error_count": errors,
        "coalesced_requests": coalesced_count,
    }


@pytest.mark.asyncio
async def test_load_harness_cached_workload():
    """Run load tests for 10, 50, 100 concurrency on CACHED workload."""
    for c in [10, 50, 100]:
        res = await run_concurrent_load_test(concurrency=c, workload_type="cached")
        assert res["error_count"] == 0
        assert res["p50_latency_ms"] < 20.0, f"Cached P50 latency too high: {res['p50_latency_ms']}ms"


@pytest.mark.asyncio
async def test_load_harness_fresh_workload():
    """Run load tests for 10, 50, 100 concurrency on FRESH workload with single-flight."""
    for c in [10, 50, 100]:
        res = await run_concurrent_load_test(concurrency=c, workload_type="fresh")
        assert res["error_count"] == 0
        assert res["coalesced_requests"] == c - 1
        assert res["p50_latency_ms"] < 100.0, f"Fresh P50 latency too high: {res['p50_latency_ms']}ms"


if __name__ == "__main__":
    async def main():
        report = []
        for wl in ["cached", "fresh"]:
            for conc in [10, 50, 100]:
                data = await run_concurrent_load_test(conc, wl)
                report.append(data)
        print(json.dumps(report, indent=2))

    asyncio.run(main())
