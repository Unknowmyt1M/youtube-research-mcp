import time
from typing import Any, Dict, List


class MetricsCollector:
    """Lightweight in-process metrics aggregator for observability."""

    def __init__(self):
        self.request_counts: Dict[str, int] = {
            "search": 0,
            "metadata": 0,
            "transcript": 0,
            "find_in_video": 0,
            "research": 0,
        }
        self.cache_stats = {
            "hits": 0,
            "misses": 0,
            "negative_hits": 0,
        }
        self.retrieval_stats = {
            "total_searches": 0,
            "total_matches_returned": 0,
            "total_latency_ms": 0.0,
        }
        self.single_flight_coalesced: int = 0
        self.start_time: float = time.time()

    def record_request(self, endpoint: str):
        if endpoint in self.request_counts:
            self.request_counts[endpoint] += 1
        else:
            self.request_counts[endpoint] = 1

    def record_cache_hit(self, is_negative: bool = False):
        if is_negative:
            self.cache_stats["negative_hits"] += 1
        else:
            self.cache_stats["hits"] += 1

    def record_cache_miss(self):
        self.cache_stats["misses"] += 1

    def record_coalesced_request(self):
        self.single_flight_coalesced += 1

    def record_retrieval(self, matches_count: int, latency_ms: float):
        self.retrieval_stats["total_searches"] += 1
        self.retrieval_stats["total_matches_returned"] += matches_count
        self.retrieval_stats["total_latency_ms"] += latency_ms

    def get_summary(self) -> Dict[str, Any]:
        uptime_sec = round(time.time() - self.start_time, 1)
        total_cache_reqs = (
            self.cache_stats["hits"]
            + self.cache_stats["misses"]
            + self.cache_stats["negative_hits"]
        )
        hit_rate = (
            round((self.cache_stats["hits"] / total_cache_reqs) * 100, 1)
            if total_cache_reqs > 0
            else 0.0
        )
        avg_retrieval_latency = (
            round(
                self.retrieval_stats["total_latency_ms"]
                / max(1, self.retrieval_stats["total_searches"]),
                2,
            )
            if self.retrieval_stats["total_searches"] > 0
            else 0.0
        )

        return {
            "uptime_seconds": uptime_sec,
            "requests": self.request_counts,
            "cache": {
                "hits": self.cache_stats["hits"],
                "misses": self.cache_stats["misses"],
                "negative_hits": self.cache_stats["negative_hits"],
                "hit_rate_pct": hit_rate,
            },
            "single_flight_coalesced": self.single_flight_coalesced,
            "retrieval": {
                "total_searches": self.retrieval_stats["total_searches"],
                "total_matches": self.retrieval_stats["total_matches_returned"],
                "avg_latency_ms": avg_retrieval_latency,
            },
        }

    get_snapshot = get_summary


# Global singleton
metrics = MetricsCollector()
