import pytest
from youtube_research_mcp.models.transcript import TranscriptChunk
from youtube_research_mcp.services.retrieval import (
    HybridRetrievalIndex,
    tokenize_multilingual,
)


def test_multilingual_tokenization():
    # Test Devanagari (Hindi)
    hindi_tokens = tokenize_multilingual("क्वांटम कंप्यूटिंग 2026 में breakthrough है")
    assert "क्वांटम" in hindi_tokens
    assert "कंप्यूटिंग" in hindi_tokens
    assert "2026" in hindi_tokens
    assert "breakthrough" in hindi_tokens

    # Test CJK (Chinese / Japanese)
    cjk_tokens = tokenize_multilingual("量子计算 突破 2026")
    assert "量子计算" in cjk_tokens
    assert "突破" in cjk_tokens

    # Test Arabic
    arabic_tokens = tokenize_multilingual("الحوسبة الكمومية 2026")
    assert "الحوسبة" in arabic_tokens
    assert "الكمومية" in arabic_tokens


def test_hindi_hybrid_retrieval():
    chunks = [
        TranscriptChunk(
            chunk_id=1,
            video_id="hindi_vid_1",
            start_seconds=0.0,
            end_seconds=60.0,
            time_range="00:00 - 01:00",
            text="नमस्ते दोस्तों, आज हम क्वांटम कंप्यूटिंग और नए क्वांटम प्रोसेसर के बारे में बात करेंगे।",
            word_count=15,
            url="https://youtu.be/hindi_vid_1?t=0",
        ),
        TranscriptChunk(
            chunk_id=2,
            video_id="hindi_vid_1",
            start_seconds=60.0,
            end_seconds=120.0,
            time_range="01:00 - 02:00",
            text="वेब डेवलपमेंट और जावास्क्रिप्ट फ्रेमवर्क के बारे में ट्यूटोरियल।",
            word_count=10,
            url="https://youtu.be/hindi_vid_1?t=60",
        ),
    ]

    index = HybridRetrievalIndex(chunks)
    matches = index.search(query="क्वांटम प्रोसेसर", top_k=2)

    assert len(matches) > 0
    assert matches[0].chunk_id == 1
    assert "क्वांटम" in matches[0].text
