import asyncio
from typing import List
import pytest

from youtube_research_mcp.models.transcript import TranscriptChunk
from youtube_research_mcp.services.retrieval import (
    HybridRetrievalIndex,
    RetrievalIndexCache,
    tokenize_multilingual,
)
from youtube_research_mcp.utils.formatting import format_timestamp, make_timestamp_url


def _make_chunk(chunk_id: int, start: float, end: float, text: str, vid: str = "test_vid") -> TranscriptChunk:
    return TranscriptChunk(
        video_id=vid,
        chunk_id=chunk_id,
        start_seconds=start,
        end_seconds=end,
        time_range=f"{format_timestamp(start)} - {format_timestamp(end)}",
        text=text,
        word_count=len(text.split()),
        url=make_timestamp_url(vid, start),
    )


def test_multilingual_tokenization_korean_hangul_and_scripts():
    """Verify multilingual tokenization supports Korean Hangul, CJK, Hindi, Spanish, English."""
    # 1. Korean Hangul
    korean_text = "안녕하세요! 유튜브 리서치 인덱스 테스트입니다."
    korean_tokens = tokenize_multilingual(korean_text)
    assert "안녕하세요" in korean_tokens
    assert "유튜브" in korean_tokens
    assert "리서치" in korean_tokens

    # 2. Hindi Devanagari
    hindi_text = "नमस्ते दुनिया! यूट्यूब अनुसंधान इंजन।"
    hindi_tokens = tokenize_multilingual(hindi_text)
    assert "नमस्ते" in hindi_tokens
    assert "दुनिया" in hindi_tokens
    assert "अनुसंधान" in hindi_tokens

    # 3. Japanese (Kanji + Kana)
    jp_text = "こんにちは世界！YouTubeリサーチ。"
    jp_tokens = tokenize_multilingual(jp_text)
    assert "こんにちは" in jp_tokens
    assert "世界" in jp_tokens

    # 4. Chinese (Hanzi)
    cn_text = "你好世界！YouTube搜索研究。"
    cn_tokens = tokenize_multilingual(cn_text)
    assert "你好世界" in cn_tokens

    # 5. Spanish / English with numbers and symbols
    sp_text = "investigación de IA en YouTube 2026-v2"
    sp_tokens = tokenize_multilingual(sp_text)
    assert "investigaci" in sp_tokens[0] or "youtube" in sp_tokens


@pytest.mark.asyncio
async def test_korean_hangul_hybrid_retrieval():
    """Verify hybrid RRF retrieval successfully finds Korean segments with Hangul queries."""
    chunks = [
        _make_chunk(
            0,
            0.0,
            10.0,
            "오늘 우리는 인공지능과 유튜브 자동화에 대해 이야기합니다.",
        ),
        _make_chunk(
            1,
            10.0,
            20.0,
            "머신러닝 모델의 성능과 검색 최적화 기술입니다.",
        ),
        _make_chunk(
            2,
            20.0,
            30.0,
            "전혀 관련 없는 일상 브이로그 요리 레시피입니다.",
        ),
    ]

    index = HybridRetrievalIndex(chunks)
    matches = index.search(query="인공지능 유튜브", top_k=2)

    assert len(matches) > 0
    assert matches[0].chunk_id == 0
    assert "인공지능" in matches[0].text


@pytest.mark.asyncio
async def test_retrieval_index_cache_concurrency_single_flight():
    """Verify 10 concurrent requests for same video build the index exactly once without poison."""
    cache = RetrievalIndexCache(max_size=5, ttl_seconds=60)
    chunks = [
        _make_chunk(0, 0.0, 5.0, "Concurrent build test segment.")
    ]

    build_count = 0
    original_init = HybridRetrievalIndex.__init__

    def counting_init(self, chs):
        nonlocal build_count
        build_count += 1
        original_init(self, chs)

    with pytest.MonkeyPatch().context() as mp:
        mp.setattr(HybridRetrievalIndex, "__init__", counting_init)

        tasks = [cache.get_or_build("video_single_flight", chunks) for _ in range(10)]
        results = await asyncio.gather(*tasks)

        assert build_count == 1
        for r in results:
            assert isinstance(r, HybridRetrievalIndex)

    # Different video builds independently
    different_chunks = [
        _make_chunk(0, 0.0, 5.0, "Different video chunk.", vid="video_different")
    ]
    diff_index = await cache.get_or_build("video_different", different_chunks)
    assert isinstance(diff_index, HybridRetrievalIndex)
