import pytest
from youtube_research_mcp.models.transcript import TranscriptChunk
from youtube_research_mcp.services.retrieval import HybridRetrievalIndex


def test_hybrid_rrf_retrieval():
    chunks = [
        TranscriptChunk(
            chunk_id="v1_c001",
            video_id="v1",
            start_seconds=0.0,
            end_seconds=60.0,
            start_formatted="00:00",
            end_formatted="01:00",
            time_range="00:00 - 01:00",
            text="Welcome to the podcast. Today we talk about baking sourdough bread and yeast fermentation.",
            url="https://youtu.be/v1?t=0",
            word_count=14,
        ),
        TranscriptChunk(
            chunk_id="v1_c002",
            video_id="v1",
            start_seconds=60.0,
            end_seconds=120.0,
            start_formatted="01:00",
            end_formatted="02:00",
            time_range="01:00 - 02:00",
            text="Quantum computing uses qubits and entanglement to perform complex matrix calculations in parallel.",
            url="https://youtu.be/v1?t=60",
            word_count=14,
        ),
        TranscriptChunk(
            chunk_id="v1_c003",
            video_id="v1",
            start_seconds=120.0,
            end_seconds=180.0,
            start_formatted="02:00",
            end_formatted="03:00",
            time_range="02:00 - 03:00",
            text="In classical computing, bits are either 0 or 1, whereas quantum superposition allows simultaneous states.",
            url="https://youtu.be/v1?t=120",
            word_count=14,
        ),
    ]

    index = HybridRetrievalIndex(chunks)

    # Search for quantum entanglement
    matches = index.search("quantum entanglement and superposition", top_k=2)

    assert len(matches) > 0
    # Top match should be either chunk 2 or 3 (quantum topics), NOT baking bread
    top_chunk_id = matches[0].chunk_id
    assert top_chunk_id in ["v1_c002", "v1_c003"]
    assert matches[0].relevance_score > 0.0
    assert "quantum" in matches[0].text.lower()
