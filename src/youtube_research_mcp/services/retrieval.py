import asyncio
from collections import OrderedDict
import logging
import math
import re
import time
import unicodedata
from typing import Any, Dict, List, Optional, Set, Tuple
import bm25s
import numpy as np

from youtube_research_mcp.config import settings
from youtube_research_mcp.models.transcript import (
    TranscriptChunk,
    TranscriptSearchMatch,
)

logger = logging.getLogger(__name__)

# Unicode-aware regex matching Latin, Devanagari (Hindi), CJK (Chinese, Japanese), Korean (Hangul), Arabic, Cyrillic tokens
MULTILINGUAL_TOKEN_PATTERN = re.compile(
    r"[\u0900-\u097F]+|[\u4e00-\u9fff]+|[\u3040-\u30ff]+|[\uac00-\ud7af]+|[\u1100-\u11ff]+|[\u0600-\u06FF]+|[\u0400-\u04FF]+|[a-zA-Z0-9_-]+"
)

# Cross-language / transliteration semantic dictionary (Devanagari Hindi <-> Hinglish <-> English)
CROSS_LINGUAL_SYNONYM_MAP: Dict[str, List[str]] = {
    # Tech & Concepts
    "quantum": ["क्वांटम", "quantum", "kvantam"],
    "क्वांटम": ["quantum", "kvantam"],
    "computing": ["कंप्यूटिंग", "कंप्यूटर", "computing", "computer"],
    "कंप्यूटिंग": ["computing", "computer"],
    "कंप्यूटर": ["computer", "computing"],
    "ai": ["आर्टिफिशियल", "इंटेलिजेंस", "कृत्रिम", "बुद्धिमत्ता", "ai", "artificial"],
    "artificial": ["आर्टिफिशियल", "कृत्रिम", "artificial"],
    "intelligence": ["इंटेलिजेंस", "बुद्धिमत्ता", "intelligence"],
    "machine": ["मशीन", "machine"],
    "मशीन": ["machine"],
    "learning": ["लर्निंग", "सीखना", "learning"],
    "लर्निंग": ["learning"],
    "neural": ["न्यूरल", "neural"],
    "न्यूरल": ["neural"],
    "network": ["नेटवर्क", "network"],
    "नेटवर्क": ["network"],
    "python": ["पायथन", "python"],
    "पायथन": ["python"],
    "code": ["कोड", "coding", "code"],
    "coding": ["कोडिंग", "coding", "code"],
    "कोड": ["code", "coding"],
    "कोडिंग": ["coding", "code"],
    "api": ["एपीआई", "api"],
    "एपीआई": ["api"],
    "database": ["डेटाबेस", "database"],
    "डेटाबेस": ["database"],
    "model": ["मॉडल", "model"],
    "मॉडल": ["model"],
    "transformer": ["ट्रांसफॉर्मर", "transformer"],
    "data": ["डेटा", "data"],
    "डेटा": ["data"],
    "youtube": ["यूट्यूब", "youtube"],
    "यूट्यूब": ["youtube"],
    "video": ["वीडियो", "video"],
    "वीडियो": ["video"],
    "research": ["अनुसंधान", "रिसर्च", "खोज", "research"],
    "अनुसंधान": ["research", "anushandhan"],
    "रिसर्च": ["research"],

    # Common Action / Query Words (Hinglish <-> Hindi <-> English)
    "explain": ["समझाया", "समझाना", "समझें", "explain", "explained", "samjhaya", "samjhana", "samjhe"],
    "explained": ["समझाया", "explain", "explained", "samjhaya"],
    "explanation": ["विवरण", "समझाया", "explanation", "samjhaya"],
    "samjhaya": ["समझाया", "explain", "explained"],
    "samjhana": ["समझाना", "explain"],
    "samjhe": ["समझें", "understand", "explain"],
    "समझाया": ["explain", "explained", "samjhaya"],
    "समझाना": ["explain", "samjhana"],
    "समझें": ["understand", "explain", "samjhe"],
    "how": ["कैसे", "how", "kaise"],
    "kaise": ["कैसे", "how"],
    "कैसे": ["how", "kaise"],
    "what": ["क्या", "what", "kya"],
    "kya": ["क्या", "what"],
    "क्या": ["what", "kya"],
    "why": ["क्यों", "why", "kyon", "kyu"],
    "kyon": ["क्यों", "why"],
    "kyu": ["क्यों", "why"],
    "क्यों": ["why", "kyon", "kyu"],
    "where": ["कहाँ", "कहा", "where", "kahan"],
    "kahan": ["कहाँ", "where"],
    "कहाँ": ["where", "kahan"],
    "when": ["कब", "when", "kab"],
    "kab": ["कब", "when"],
    "कब": ["when", "kab"],
    "use": ["उपयोग", "इस्तेमाल", "use", "using", "istamal", "istemaal"],
    "using": ["उपयोग", "इस्तेमाल", "use", "using"],
    "istamal": ["इस्तेमाल", "उपयोग", "use"],
    "istemaal": ["इस्तेमाल", "उपयोग", "use"],
    "उपयोग": ["use", "using", "usage"],
    "इस्तेमाल": ["use", "using", "istamal"],
    "work": ["काम", "कार्य", "work", "works", "working", "kaam"],
    "works": ["काम", "work", "works", "kaam"],
    "working": ["काम", "कार्य", "working", "kaam"],
    "kaam": ["काम", "work", "works"],
    "काम": ["work", "works", "working", "kaam"],
    "start": ["शुरू", "शुरुआत", "start", "starting", "intro", "shuru"],
    "shuru": ["शुरू", "start", "intro"],
    "शुरू": ["start", "intro", "shuru"],
    "conclusion": ["निष्कर्ष", "अंत", "conclusion", "summary", "ant"],
    "summary": ["सारांश", "summary", "conclusion"],
    "निष्कर्ष": ["conclusion", "summary"],
    "अंत": ["conclusion", "end", "ant"],
    "difference": ["अंतर", "difference", "diff", "antar"],
    "antar": ["अंतर", "difference"],
    "अंतर": ["difference", "antar"],
    "feature": ["फीचर", "विशेषता", "feature", "features"],
    "फीचर": ["feature", "features"],
    "tutorial": ["ट्यूटोरियल", "tutorial", "guide", "guide"],
    "ट्यूटोरियल": ["tutorial", "guide"],
    "architecture": ["आर्किटेक्चर", "संरचना", "architecture"],
    "आर्किटेक्चर": ["architecture"],
}


def normalize_query(query: str) -> str:
    """Normalize query string safely: NFKC Unicode normalization, whitespace trimming, preserving tokens."""
    if not query:
        return ""
    # Unicode NFKC normalization decomposes compatibility forms and recomposes canon
    norm = unicodedata.normalize("NFKC", query)
    # Collapse multiple whitespace characters
    norm = re.sub(r"\s+", " ", norm).strip()
    return norm


def detect_script(text: str) -> str:
    """Detect dominant writing script of a text (devanagari, cjk, hangul, arabic, cyrillic, latin, mixed)."""
    counts = {
        "devanagari": len(re.findall(r"[\u0900-\u097F]", text)),
        "cjk": len(re.findall(r"[\u4e00-\u9fff\u3040-\u30ff]", text)),
        "hangul": len(re.findall(r"[\uac00-\ud7af\u1100-\u11ff]", text)),
        "arabic": len(re.findall(r"[\u0600-\u06FF]", text)),
        "cyrillic": len(re.findall(r"[\u0400-\u04FF]", text)),
        "latin": len(re.findall(r"[a-zA-Z]", text)),
    }
    total = sum(counts.values())
    if total == 0:
        return "unknown"

    dominant_script, max_count = max(counts.items(), key=lambda x: x[1])
    if max_count / total >= 0.5:
        return dominant_script
    return "mixed"


def tokenize_multilingual(text: str) -> List[str]:
    """Tokenize multi-script text (Hindi, CJK, Hangul, Arabic, Cyrillic, English)."""
    norm_text = normalize_query(text)
    return [t.lower() for t in MULTILINGUAL_TOKEN_PATTERN.findall(norm_text)]


def expand_cross_lingual_tokens(tokens: List[str]) -> List[str]:
    """Expand tokens with cross-lingual synonyms and transliteration bridging terms."""
    expanded: List[str] = list(tokens)
    for t in tokens:
        low_t = t.lower()
        if low_t in CROSS_LINGUAL_SYNONYM_MAP:
            for syn in CROSS_LINGUAL_SYNONYM_MAP[low_t]:
                if syn not in expanded:
                    expanded.append(syn)
    return expanded


def generate_subword_ngrams(tokens: List[str], min_n: int = 3, max_n: int = 4) -> List[str]:
    """Generate character n-grams from word tokens to support morphological and transliteration matching."""
    ngrams: List[str] = []
    for token in tokens:
        if len(token) < min_n:
            continue
        for n in range(min_n, min(max_n + 1, len(token) + 1)):
            for i in range(len(token) - n + 1):
                ngrams.append(token[i : i + n])
    return ngrams


_global_embedder: Optional[Any] = None
_embedder_checked: bool = False


def get_embedder() -> Optional[Any]:
    global _global_embedder, _embedder_checked
    if not settings.USE_ONNX_EMBEDDER:
        return None

    if _embedder_checked:
        return _global_embedder

    _embedder_checked = True
    try:
        from fastembed import TextEmbedding

        _global_embedder = TextEmbedding(model_name=settings.EMBEDDING_MODEL)
    except (ImportError, OSError, Exception) as e:
        logger.warning(f"Dense embedder unavailable ({e}), using multilingual subword vector fallback.")
        _global_embedder = None

    return _global_embedder


class MultilingualSubwordTfidf:
    """Multilingual in-process TF-IDF vectorizer with cross-lingual vocabulary bridging and character n-grams."""

    def __init__(self):
        self.vocab: Dict[str, int] = {}
        self.idf: np.ndarray = np.array([], dtype=np.float32)

    def _extract_features(self, text: str) -> List[str]:
        tokens = tokenize_multilingual(text)
        expanded_tokens = expand_cross_lingual_tokens(tokens)
        subwords = generate_subword_ngrams(expanded_tokens, min_n=3, max_n=4)
        return expanded_tokens + subwords

    def fit_transform(self, docs: List[str]) -> np.ndarray:
        doc_features = [self._extract_features(doc) for doc in docs]
        vocab_set: Set[str] = set()
        for feats in doc_features:
            vocab_set.update(feats)

        self.vocab = {term: idx for idx, term in enumerate(sorted(vocab_set))}
        vocab_size = len(self.vocab)
        num_docs = len(docs)

        if vocab_size == 0 or num_docs == 0:
            return np.zeros((num_docs, 1), dtype=np.float32)

        df = np.zeros(vocab_size, dtype=np.float32)
        tf_matrix = np.zeros((num_docs, vocab_size), dtype=np.float32)

        for i, feats in enumerate(doc_features):
            seen_in_doc: Set[int] = set()
            for term in feats:
                idx = self.vocab[term]
                tf_matrix[i, idx] += 1
                seen_in_doc.add(idx)
            for idx in seen_in_doc:
                df[idx] += 1

        self.idf = np.log((num_docs + 1) / (df + 1)) + 1.0
        tfidf = tf_matrix * self.idf
        norms = np.linalg.norm(tfidf, axis=1, keepdims=True)
        return tfidf / np.maximum(norms, 1e-9)

    def transform(self, query: str) -> np.ndarray:
        feats = self._extract_features(query)
        vocab_size = len(self.vocab)
        if vocab_size == 0:
            return np.zeros(1, dtype=np.float32)

        tf = np.zeros(vocab_size, dtype=np.float32)
        for t in feats:
            if t in self.vocab:
                tf[self.vocab[t]] += 1

        tfidf = tf * self.idf
        norm = np.linalg.norm(tfidf)
        return tfidf / max(norm, 1e-9)


# Backwards compatibility alias for research engine
LexicalTfidfFallback = MultilingualSubwordTfidf


class HybridRetrievalIndex:
    """In-process hybrid retrieval engine combining dense vectors (or multilingual subword TF-IDF) with BM25s sparse index."""

    def __init__(self, chunks: List[TranscriptChunk]):
        self.chunks = chunks
        self.corpus_texts = [c.text for c in chunks]
        self.embedder = get_embedder()
        self.tfidf_fallback: Optional[MultilingualSubwordTfidf] = None
        self.is_dense_semantic: bool = self.embedder is not None

        if self.embedder is not None:
            try:
                raw_embeds = list(self.embedder.embed(self.corpus_texts))
                self.embeddings = np.array(raw_embeds, dtype=np.float32)
                norms = np.linalg.norm(self.embeddings, axis=1, keepdims=True)
                self.embeddings = self.embeddings / np.maximum(norms, 1e-9)
            except Exception:
                self.embedder = None
                self.is_dense_semantic = False

        if self.embedder is None:
            self.tfidf_fallback = MultilingualSubwordTfidf()
            self.embeddings = self.tfidf_fallback.fit_transform(self.corpus_texts)

        # Build BM25 sparse index with cross-lingual expanded tokens (without raw subword n-grams)
        tokenized_corpus = []
        for text in self.corpus_texts:
            tokens = tokenize_multilingual(text)
            expanded = expand_cross_lingual_tokens(tokens)
            tokenized_corpus.append(expanded)

        self.bm25 = bm25s.BM25(k1=settings.BM25_K1, b=settings.BM25_B)
        self.bm25.index(tokenized_corpus, show_progress=False)

    def search(
        self, query: str, top_k: int = 5, k_rrf: int = 60
    ) -> List[TranscriptSearchMatch]:
        if not self.chunks:
            return []

        norm_query = normalize_query(query)
        if not norm_query:
            return []

        num_docs = len(self.chunks)
        effective_k = min(num_docs, max(top_k * 3, 10))

        # --- A. Dense / Multilingual Subword TF-IDF Similarity ---
        if self.embedder is not None:
            try:
                query_embed = np.array(
                    list(self.embedder.embed([norm_query])), dtype=np.float32
                )[0]
                query_norm = np.linalg.norm(query_embed)
                query_embed = query_embed / max(query_norm, 1e-9)
                dense_scores = np.dot(self.embeddings, query_embed)
            except Exception:
                dense_scores = np.zeros(num_docs, dtype=np.float32)
        elif self.tfidf_fallback is not None:
            query_vec = self.tfidf_fallback.transform(norm_query)
            dense_scores = np.dot(self.embeddings, query_vec)
        else:
            dense_scores = np.zeros(num_docs, dtype=np.float32)

        dense_ranked_indices = np.argsort(-dense_scores)
        dense_rank_map = {
            int(idx): rank for rank, idx in enumerate(dense_ranked_indices)
        }

        # --- B. Sparse BM25 Retrieval ---
        query_tokens = tokenize_multilingual(norm_query)
        expanded_query_tokens = expand_cross_lingual_tokens(query_tokens)
        search_tokens = [expanded_query_tokens]

        bm25_docs, bm25_scores = self.bm25.retrieve(
            search_tokens, k=min(num_docs, effective_k), show_progress=False
        )

        bm25_rank_map: Dict[int, int] = {}
        bm25_score_map: Dict[int, float] = {}
        if len(bm25_docs) > 0:
            for rank, doc_idx in enumerate(bm25_docs[0]):
                idx_int = int(doc_idx)
                bm25_rank_map[idx_int] = rank
                if len(bm25_scores) > 0:
                    bm25_score_map[idx_int] = float(bm25_scores[0][rank])

        # Define stopwords to isolate content tokens
        stopwords = {
            "a", "an", "the", "and", "or", "but", "in", "on", "at", "to", "for",
            "with", "by", "from", "of", "up", "about", "into", "over", "after",
            "is", "are", "was", "were", "be", "been", "being", "have", "has",
            "had", "do", "does", "did", "will", "would", "shall", "should",
            "can", "could", "may", "might", "must", "i", "you", "he", "she",
            "it", "we", "they", "me", "him", "her", "us", "them", "my", "your",
            "his", "their", "our", "what", "which", "who", "whom", "this",
            "that", "these", "those", "how", "why", "where", "when", "is", "are"
        }
        content_query_tokens = [
            t for t in query_tokens if t not in stopwords and len(t) > 1
        ]

        # --- C. Reciprocal Rank Fusion (RRF) with Multi-Signal Boosting ---
        low_query = norm_query.lower()
        fused: List[Tuple[float, float, int]] = []

        for idx in range(num_docs):
            chunk_text = self.chunks[idx].text.lower()
            r_dense = dense_rank_map.get(idx, 9999)
            r_sparse = bm25_rank_map.get(idx, 9999)

            score_dense = 1.0 / (k_rrf + r_dense)
            score_sparse = (
                1.0 / (k_rrf + r_sparse) if idx in bm25_rank_map else 0.0
            )

            rrf_base = score_dense + score_sparse

            # 1. Exact phrase boost
            phrase_boost = 0.0
            if len(low_query) > 3 and low_query in chunk_text:
                phrase_boost = 0.02

            # 2. Query terms coverage boost & content term count
            coverage_boost = 0.0
            matched_content_count = 0
            if query_tokens:
                matched_count = sum(
                    1
                    for qt in query_tokens
                    if qt in chunk_text
                    or any(syn in chunk_text for syn in CROSS_LINGUAL_SYNONYM_MAP.get(qt, []))
                )
                coverage_ratio = matched_count / len(query_tokens)
                coverage_boost = 0.015 * coverage_ratio

            if content_query_tokens:
                matched_content_count = sum(
                    1
                    for qt in content_query_tokens
                    if qt in chunk_text
                    or any(syn in chunk_text for syn in CROSS_LINGUAL_SYNONYM_MAP.get(qt, []))
                )

            total_score = rrf_base + phrase_boost + coverage_boost

            # Compute absolute confidence score
            sim_dense = max(0.0, float(dense_scores[idx]))
            bm25_val = bm25_score_map.get(idx, 0.0)
            sim_bm25 = max(0.0, min(1.0, bm25_val / 5.0))

            if self.is_dense_semantic:
                abs_confidence = max(sim_dense, sim_bm25 * 0.8)
            else:
                # TF-IDF fallback mode: blend TF-IDF similarity with term overlap
                content_coverage = (
                    matched_content_count / max(len(content_query_tokens), 1)
                    if content_query_tokens
                    else 0.0
                )
                abs_confidence = max(sim_dense, sim_bm25 * 0.7, content_coverage * 0.5)

            # Rejection Gate for false positives:
            # If query has distinct non-stopword content tokens, require either:
            # - At least 1 matched content token (or cross-lingual synonym), OR
            # - Dense semantic similarity >= 0.42 (for implicit/conceptual matches in dense mode)
            if content_query_tokens and matched_content_count == 0:
                if self.is_dense_semantic:
                    if sim_dense < 0.42:
                        continue  # Reject false positive match
                else:
                    continue  # Reject false positive in TF-IDF mode

            if abs_confidence < 0.20:
                continue

            fused.append((total_score, abs_confidence, idx))

        fused.sort(key=lambda x: x[0], reverse=True)

        matches: List[TranscriptSearchMatch] = []
        for rrf_score, abs_conf, idx in fused[:top_k]:
            chunk = self.chunks[idx]
            norm_score = round(min(1.0, max(0.0, abs_conf)), 3)

            matches.append(
                TranscriptSearchMatch(
                    chunk_id=chunk.chunk_id,
                    video_id=chunk.video_id,
                    time_range=chunk.time_range,
                    start_seconds=chunk.start_seconds,
                    end_seconds=chunk.end_seconds,
                    relevance_score=norm_score,
                    text=chunk.text,
                    url=chunk.url,
                    chapter_title=chunk.chapter_title,
                )
            )

        return matches


class RetrievalIndexCache:
    """Bounded in-memory LRU cache with TTL and concurrent per-key locking for retrieval indexes."""

    def __init__(
        self,
        max_size: int = settings.MAX_RETRIEVAL_INDEXES,
        ttl_seconds: int = settings.INDEX_TTL_SECONDS,
    ):
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds
        self._cache: OrderedDict[str, Tuple[HybridRetrievalIndex, float]] = OrderedDict()
        self._locks: Dict[str, asyncio.Lock] = {}
        self._global_lock = asyncio.Lock()

    def get(self, video_id: str) -> Optional[HybridRetrievalIndex]:
        now = time.time()
        if video_id in self._cache:
            index, created_at = self._cache[video_id]
            if now - created_at <= self.ttl_seconds:
                self._cache.move_to_end(video_id)
                return index
            else:
                del self._cache[video_id]
        return None

    def put(self, video_id: str, index: HybridRetrievalIndex):
        now = time.time()
        if video_id in self._cache:
            self._cache.move_to_end(video_id)
        self._cache[video_id] = (index, now)

        if len(self._cache) > self.max_size:
            self._cache.popitem(last=False)  # Evict oldest

    async def get_or_build(
        self, video_id: str, chunks: List[TranscriptChunk]
    ) -> HybridRetrievalIndex:
        """Retrieve cached index or build once per video_id concurrently."""
        cached = self.get(video_id)
        if cached:
            return cached

        # Acquire or create per-video lock
        async with self._global_lock:
            if video_id not in self._locks:
                self._locks[video_id] = asyncio.Lock()
            video_lock = self._locks[video_id]

        async with video_lock:
            # Double-check after acquiring lock
            cached = self.get(video_id)
            if cached:
                return cached

            new_index = HybridRetrievalIndex(chunks)
            self.put(video_id, new_index)
            return new_index


_index_cache = RetrievalIndexCache()


def get_retrieval_index(
    video_id: str, chunks: List[TranscriptChunk]
) -> HybridRetrievalIndex:
    cached = _index_cache.get(video_id)
    if cached:
        return cached

    new_index = HybridRetrievalIndex(chunks)
    _index_cache.put(video_id, new_index)
    return new_index


async def get_retrieval_index_async(
    video_id: str, chunks: List[TranscriptChunk]
) -> HybridRetrievalIndex:
    return await _index_cache.get_or_build(video_id, chunks)
