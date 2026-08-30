import pytest
from tests.evaluation.evaluate_retrieval import run_retrieval_evaluation


def test_retrieval_evaluation_benchmark_thresholds():
    """Verify that retrieval evaluation achieves high recall, MRR, and zero duplicate/empty rates."""
    metrics = run_retrieval_evaluation()

    assert metrics["total_test_cases"] >= 7
    assert metrics["recall_at_1"] >= 0.85, f"Recall@1 too low: {metrics['recall_at_1']}"
    assert metrics["recall_at_3"] >= 0.95, f"Recall@3 too low: {metrics['recall_at_3']}"
    assert metrics["mrr"] >= 0.85, f"MRR too low: {metrics['mrr']}"
    assert metrics["timestamp_accuracy"] >= 0.85, f"Timestamp accuracy too low: {metrics['timestamp_accuracy']}"
    assert metrics["duplicate_rate"] == 0.0, f"Unexpected duplicates found: {metrics['duplicate_rate']}"
    assert metrics["empty_result_rate"] == 0.0, f"Unexpected empty results: {metrics['empty_result_rate']}"

    # Verify all individual cases passed
    for case in metrics["cases"]:
        assert case["success"] is True, f"Failed case {case['id']}: {case['query']}"
