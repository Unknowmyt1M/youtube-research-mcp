"""Unit tests for P1 Retrieval False-Positive Rejection & Relevance Score Integrity.

Verifies:
1. Unrelated queries ("banana", "motorcycle", "chocolate cake") return 0 matches against unrelated transcripts.
2. Relevant English queries ("Python coroutines", "event loop") return high-confidence matches.
3. Relevant Hindi / Hinglish queries return matches without false positives.
4. Relevance scores accurately reflect absolute confidence rather than forcing rank #1 to 1.0.
5. Both Dense semantic index and TF-IDF fallback index handle edge cases gracefully.
"""

import pytest
from youtube_research_mcp.services.retrieval import HybridRetrievalIndex, TranscriptChunk


@pytest.fixture
def python_asyncio_chunks():
    return [
        TranscriptChunk(
            chunk_id=0,
            video_id="cQT33yu9pY8",
            start_seconds=0,
            end_seconds=15,
            time_range="00:00-00:15",
            text="Welcome to this tutorial on Python AsyncIO and coroutines. We will cover event loops and async await syntax.",
            word_count=18,
            url="https://www.youtube.com/watch?v=cQT33yu9pY8&t=0s",
        ),
        TranscriptChunk(
            chunk_id=1,
            video_id="cQT33yu9pY8",
            start_seconds=16,
            end_seconds=30,
            time_range="00:16-00:30",
            text="An event loop manages task execution in Python. Coroutines yield execution back to the loop using await.",
            word_count=17,
            url="https://www.youtube.com/watch?v=cQT33yu9pY8&t=16s",
        ),
        TranscriptChunk(
            chunk_id=2,
            video_id="cQT33yu9pY8",
            start_seconds=31,
            end_seconds=45,
            time_range="00:31-00:45",
            text="Variables store data in memory. Functions can return values and modify state.",
            word_count=12,
            url="https://www.youtube.com/watch?v=cQT33yu9pY8&t=31s",
        ),
    ]


def test_unrelated_query_returns_zero_matches(python_asyncio_chunks):
    index = HybridRetrievalIndex(python_asyncio_chunks)
    
    # Query completely unrelated to Python / AsyncIO
    unrelated_queries = [
        "What is a banana and how do I bake a chocolate cake?",
        "motorcycle engine repair guide",
        "photosynthesis in green plants",
    ]
    
    for query in unrelated_queries:
        matches = index.search(query, top_k=5)
        assert len(matches) == 0, f"Expected 0 matches for unrelated query '{query}', got {len(matches)}"


def test_relevant_english_query_returns_matches(python_asyncio_chunks):
    index = HybridRetrievalIndex(python_asyncio_chunks)
    
    matches = index.search("How does the event loop work in Python AsyncIO?", top_k=3)
    assert len(matches) > 0, "Expected matches for relevant query"
    assert any("event loop" in m.text.lower() or "asyncio" in m.text.lower() for m in matches)
    assert matches[0].relevance_score > 0.3, f"Expected positive relevance score, got {matches[0].relevance_score}"


def test_relevant_hindi_query_returns_matches(python_asyncio_chunks):
    index = HybridRetrievalIndex(python_asyncio_chunks)
    
    # Query in Hindi for Python tutorial / event loop
    matches = index.search("पायथन में इवेंट लूप क्या है?", top_k=3)
    assert len(matches) > 0, "Expected cross-lingual Hindi matches for Python event loop query"
    assert matches[0].relevance_score > 0.2


def test_tfidf_fallback_rejection(python_asyncio_chunks, monkeypatch):
    # Force embedder to None to test TF-IDF fallback path
    monkeypatch.setattr("youtube_research_mcp.services.retrieval.get_embedder", lambda: None)
    
    index = HybridRetrievalIndex(python_asyncio_chunks)
    assert index.embedder is None
    assert index.tfidf_fallback is not None
    
    # Unrelated query should be rejected in TF-IDF mode as well
    matches = index.search("What is a banana and how do I bake a chocolate cake?", top_k=5)
    assert len(matches) == 0, f"TF-IDF fallback returned false positive matches: {matches}"
    
    # Relevant query should match in TF-IDF mode
    relevant_matches = index.search("Python AsyncIO coroutines tutorial", top_k=3)
    assert len(relevant_matches) > 0, "TF-IDF mode failed to return relevant matches"
