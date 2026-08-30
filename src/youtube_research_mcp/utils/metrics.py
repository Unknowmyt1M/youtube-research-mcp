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
        self.transcript_stats: Dict[str, Any] = {
            "total_requests": 0,
            "cache_hits": 0,
            "free_direct_successes": 0,
            "free_proxy_successes": 0,
            "supadata_calls": 0,
            "supadata_avoided": 0,
            "provenance": {},
        }
        self.single_flight_coalesced: int = 0
        self.start_time: float = time.time()

    def record_request(self, endpoint: str):
        if endpoint in self.request_counts:
            self.request_counts[endpoint] += 1
        else:
            self.request_counts[endpoint] = 1
        if endpoint == "transcript":
            self.transcript_stats["total_requests"] += 1

    def record_cache_hit(self, is_negative: bool = False):
        if is_negative:
            self.cache_stats["negative_hits"] += 1
        else:
            self.cache_stats["hits"] += 1
            self.transcript_stats["cache_hits"] += 1
            self.record_supadata_avoided()

    def record_cache_miss(self):
        self.cache_stats["misses"] += 1

    def record_coalesced_request(self):
        self.single_flight_coalesced += 1

    def record_retrieval(self, matches_count: int, latency_ms: float):
        self.retrieval_stats["total_searches"] += 1
        self.retrieval_stats["total_matches_returned"] += matches_count
        self.retrieval_stats["total_latency_ms"] += latency_ms

    def record_transcript_success(self, provider: str):
        prov = provider or "unknown"
        prov_dict = self.transcript_stats["provenance"]
        prov_dict[prov] = prov_dict.get(prov, 0) + 1

        if "residential_proxy" in prov or "proxy" in prov.lower():
            self.transcript_stats["free_proxy_successes"] += 1
            self.record_supadata_avoided()
        elif "supadata" in prov.lower():
            self.record_supadata_call()
        elif prov != "cache":
            self.transcript_stats["free_direct_successes"] += 1
            self.record_supadata_avoided()

    def record_supadata_call(self):
        self.transcript_stats["supadata_calls"] += 1

    def record_supadata_avoided(self):
        self.transcript_stats["supadata_avoided"] += 1

    def get_supadata_avoidance_rate(self) -> float:
        calls = self.transcript_stats["supadata_calls"]
        avoided = self.transcript_stats["supadata_avoided"]
        total_resolved = calls + avoided
        if total_resolved == 0:
            return 1.0
        return round(avoided / total_resolved, 4)

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
            "transcripts": {
                "total_requests": self.transcript_stats["total_requests"],
                "cache_hits": self.transcript_stats["cache_hits"],
                "free_direct_successes": self.transcript_stats["free_direct_successes"],
                "free_proxy_successes": self.transcript_stats["free_proxy_successes"],
                "supadata_calls": self.transcript_stats["supadata_calls"],
                "supadata_avoided": self.transcript_stats["supadata_avoided"],
                "supadata_avoidance_rate_pct": round(self.get_supadata_avoidance_rate() * 100.0, 2),
                "provenance": self.transcript_stats["provenance"],
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
