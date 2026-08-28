import asyncio
import time
import numpy as np
import pytest

from youtube_research_mcp.cache import get_cache
from youtube_research_mcp.services.search import SearchService
from youtube_research_mcp.services.metadata import MetadataService
from youtube_research_mcp.services.transcripts import TranscriptService


def calculate_percentiles(latencies: list[float]) -> dict:
    """Calculate P50, P90, P95, P99 in milliseconds."""
    arr = np.array(latencies) * 1000.0
    return {
        "p50": round(float(np.percentile(arr, 50)), 2),
        "p90": round(float(np.percentile(arr, 90)), 2),
        "p95": round(float(np.percentile(arr, 95)), 2),
        "p99": round(float(np.percentile(arr, 99)), 2),
    }


@pytest.mark.asyncio
async def test_benchmark_suite():
    search_service = SearchService()
    metadata_service = MetadataService()
    transcript_service = TranscriptService()
    cache = get_cache()

    video_id = "dQw4w9WgXcQ"
    queries = [
        "quantum computing",
        "system design interview",
        "artificial intelligence",
    ]

    print("\n" + "=" * 65)
    print("      YOUTUBE RESEARCH MCP — LATENCY BENCHMARK SUITE")
    print("=" * 65)

    # 1. Search Benchmark (Fresh vs Cached)
    search_fresh_latencies = []
    for q in queries:
        # Clear cache for query
        t0 = time.perf_counter()
        await search_service.search(q, max_results=5)
        search_fresh_latencies.append(time.perf_counter() - t0)

    search_cached_latencies = []
    for q in queries * 5:
        t0 = time.perf_counter()
        await search_service.search(q, max_results=5)
        search_cached_latencies.append(time.perf_counter() - t0)

    sf = calculate_percentiles(search_fresh_latencies)
    sc = calculate_percentiles(search_cached_latencies)

    print(f"\n[SEARCH BENCHMARK]")
    print(f"Fresh Search (N={len(search_fresh_latencies)}):   P50: {sf['p50']}ms | P90: {sf['p90']}ms | P95: {sf['p95']}ms | P99: {sf['p99']}ms")
    print(f"Cached Search (N={len(search_cached_latencies)}):  P50: {sc['p50']}ms | P90: {sc['p90']}ms | P95: {sc['p95']}ms | P99: {sc['p99']}ms")

    # 2. Metadata Benchmark
    meta_fresh_latencies = []
    t0 = time.perf_counter()
    await metadata_service.get_video_overview(video_id)
    meta_fresh_latencies.append(time.perf_counter() - t0)

    meta_cached_latencies = []
    for _ in range(10):
        t0 = time.perf_counter()
        await metadata_service.get_video_overview(video_id)
        meta_cached_latencies.append(time.perf_counter() - t0)

    mf = calculate_percentiles(meta_fresh_latencies)
    mc = calculate_percentiles(meta_cached_latencies)

    print(f"\n[METADATA BENCHMARK]")
    print(f"Fresh Metadata:        P50: {mf['p50']}ms | P95: {mf['p95']}ms")
    print(f"Cached Metadata (N=10): P50: {mc['p50']}ms | P95: {mc['p95']}ms")

    # 3. Transcript & Hybrid Search Benchmark
    tx_fresh_latencies = []
    t0 = time.perf_counter()
    await transcript_service.get_transcript(video_id)
    tx_fresh_latencies.append(time.perf_counter() - t0)

    tx_cached_latencies = []
    for _ in range(10):
        t0 = time.perf_counter()
        await transcript_service.get_transcript(video_id)
        tx_cached_latencies.append(time.perf_counter() - t0)

    tf = calculate_percentiles(tx_fresh_latencies)
    tc = calculate_percentiles(tx_cached_latencies)

    print(f"\n[TRANSCRIPT BENCHMARK]")
    print(f"Fresh Transcript:        P50: {tf['p50']}ms | P95: {tf['p95']}ms")
    print(f"Cached Transcript (N=10): P50: {tc['p50']}ms | P95: {tc['p95']}ms")

    # 4. In-Video Hybrid RRF Search
    find_latencies = []
    for _ in range(5):
        t0 = time.perf_counter()
        await transcript_service.find_in_video(video_id, "give you up", max_results=3)
        find_latencies.append(time.perf_counter() - t0)

    ff = calculate_percentiles(find_latencies)
    print(f"\n[HYBRID RRF RETRIEVAL (In-Video)]")
    print(f"Semantic Search (N=5):    P50: {ff['p50']}ms | P90: {ff['p90']}ms | P95: {ff['p95']}ms")
    print("=" * 65 + "\n")
