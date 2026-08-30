import json
from pathlib import Path
import sys
from typing import Any, Dict, List, Optional

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from youtube_research_mcp.models.transcript import TranscriptChunk
from youtube_research_mcp.services.retrieval import HybridRetrievalIndex
from youtube_research_mcp.utils.formatting import make_timestamp_url


def run_retrieval_evaluation(dataset_path: Optional[Path] = None) -> Dict[str, Any]:
    if dataset_path is None:
        dataset_path = Path(__file__).parent / "dataset.json"

    with open(dataset_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    test_cases = data.get("test_cases", [])
    total_cases = len(test_cases)
    if total_cases == 0:
        return {}

    hits_at_1 = 0
    hits_at_3 = 0
    hits_at_5 = 0
    reciprocal_ranks: List[float] = []
    timestamp_correct = 0
    total_returned_matches = 0
    duplicate_matches = 0
    empty_results = 0

    case_results = []

    for case in test_cases:
        vid = case["video_id"]
        query = case["query"]
        expected_chunk_id = case["expected_chunk_id"]
        expected_time_range = case["expected_time_range"]

        raw_chunks = case["chunks"]
        chunks = [
            TranscriptChunk(
                video_id=vid,
                chunk_id=c["chunk_id"],
                start_seconds=c["start_seconds"],
                end_seconds=c["end_seconds"],
                time_range=c["time_range"],
                text=c["text"],
                word_count=len(c["text"].split()),
                url=make_timestamp_url(vid, c["start_seconds"]),
            )
            for c in raw_chunks
        ]

        index = HybridRetrievalIndex(chunks)
        matches = index.search(query=query, top_k=5)

        total_returned_matches += len(matches)
        if len(matches) == 0:
            empty_results += 1
            reciprocal_ranks.append(0.0)
            case_results.append({
                "id": case["id"],
                "category": case["category"],
                "rank": None,
                "success": False,
            })
            continue

        # Check for duplicates
        seen_chunk_ids = set()
        for m in matches:
            if m.chunk_id in seen_chunk_ids:
                duplicate_matches += 1
            seen_chunk_ids.add(m.chunk_id)

        # Calculate rank of expected chunk
        rank_found = None
        for r_idx, match in enumerate(matches):
            if match.chunk_id == expected_chunk_id:
                rank_found = r_idx + 1
                break

        if rank_found == 1:
            hits_at_1 += 1
        if rank_found and rank_found <= 3:
            hits_at_3 += 1
        if rank_found and rank_found <= 5:
            hits_at_5 += 1

        if rank_found:
            reciprocal_ranks.append(1.0 / rank_found)
            # Timestamp accuracy: top match matches expected time range
            if matches[0].chunk_id == expected_chunk_id or matches[0].time_range == expected_time_range:
                timestamp_correct += 1
        else:
            reciprocal_ranks.append(0.0)

        case_results.append({
            "id": case["id"],
            "category": case["category"],
            "query": query,
            "expected_chunk_id": expected_chunk_id,
            "rank": rank_found,
            "top_match_id": matches[0].chunk_id if matches else None,
            "top_match_score": matches[0].relevance_score if matches else 0.0,
            "success": (rank_found is not None and rank_found <= 3),
        })

    metrics_output = {
        "total_test_cases": total_cases,
        "recall_at_1": round(hits_at_1 / total_cases, 4),
        "recall_at_3": round(hits_at_3 / total_cases, 4),
        "recall_at_5": round(hits_at_5 / total_cases, 4),
        "mrr": round(sum(reciprocal_ranks) / total_cases, 4),
        "timestamp_accuracy": round(timestamp_correct / total_cases, 4),
        "duplicate_rate": round(duplicate_matches / max(1, total_returned_matches), 4),
        "empty_result_rate": round(empty_results / total_cases, 4),
        "cases": case_results,
    }

    return metrics_output


if __name__ == "__main__":
    res = run_retrieval_evaluation()
    print(json.dumps(res, indent=2, ensure_ascii=False))
