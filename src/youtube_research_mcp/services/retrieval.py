import math
import re
from typing import Any, List, Optional
import bm25s
import numpy as np

from youtube_research_mcp.config import settings
from youtube_research_mcp.models.transcript import (
    TranscriptChunk,
    TranscriptSearchMatch,
)

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
    except (ImportError, OSError, Exception):
        _global_embedder = None

    return _global_embedder


class SimpleTfidfEmbedder:
    """Pure NumPy in-process TF-IDF vectorizer fallback when ONNX runtime is unavailable."""

    def __init__(self):
        self.vocab: dict[str, int] = {}
        self.idf: np.ndarray = np.array([], dtype=np.float32)

    def fit_transform(self, docs: List[str]) -> np.ndarray:
        tokenized_docs = [
            re.findall(r"\b[a-zA-Z0-9_-]+\b", doc.lower()) for doc in docs
        ]
        vocab_set = set()
        for doc in tokenized_docs:
            vocab_set.update(doc)

        self.vocab = {term: idx for idx, term in enumerate(sorted(vocab_set))}
        vocab_size = len(self.vocab)
        num_docs = len(docs)

        if vocab_size == 0 or num_docs == 0:
            return np.zeros((num_docs, 1), dtype=np.float32)

        # Document frequencies
        df = np.zeros(vocab_size, dtype=np.float32)
        tf_matrix = np.zeros((num_docs, vocab_size), dtype=np.float32)

        for i, doc in enumerate(tokenized_docs):
            seen_in_doc = set()
            for term in doc:
                idx = self.vocab[term]
                tf_matrix[i, idx] += 1
                seen_in_doc.add(idx)
            for idx in seen_in_doc:
                df[idx] += 1

        # Smooth IDF
        self.idf = np.log((num_docs + 1) / (df + 1)) + 1.0

        tfidf = tf_matrix * self.idf
        # L2 normalize
        norms = np.linalg.norm(tfidf, axis=1, keepdims=True)
        return tfidf / np.maximum(norms, 1e-9)

    def transform(self, query: str) -> np.ndarray:
        tokens = re.findall(r"\b[a-zA-Z0-9_-]+\b", query.lower())
        vocab_size = len(self.vocab)
        if vocab_size == 0:
            return np.zeros(1, dtype=np.float32)

        tf = np.zeros(vocab_size, dtype=np.float32)
        for t in tokens:
            if t in self.vocab:
                tf[self.vocab[t]] += 1

        tfidf = tf * self.idf
        norm = np.linalg.norm(tfidf)
        return tfidf / max(norm, 1e-9)


class HybridRetrievalIndex:
    """In-process hybrid retrieval engine combining dense vectors with BM25s sparse index."""

    def __init__(self, chunks: List[TranscriptChunk]):
        self.chunks = chunks
        self.corpus_texts = [c.text for c in chunks]
        self.embedder = get_embedder()
        self.tfidf_fallback = None

        if self.embedder is not None:
            try:
                raw_embeds = list(self.embedder.embed(self.corpus_texts))
                self.embeddings = np.array(raw_embeds, dtype=np.float32)
                norms = np.linalg.norm(self.embeddings, axis=1, keepdims=True)
                self.embeddings = self.embeddings / np.maximum(norms, 1e-9)
            except Exception:
                self.embedder = None

        if self.embedder is None:
            # Use pure NumPy TF-IDF
            self.tfidf_fallback = SimpleTfidfEmbedder()
            self.embeddings = self.tfidf_fallback.fit_transform(
                self.corpus_texts
            )

        # Build BM25 sparse index
        corpus_tokens = bm25s.tokenize(self.corpus_texts, stopwords="en")
        self.bm25 = bm25s.BM25(k1=settings.BM25_K1, b=settings.BM25_B)
        self.bm25.index(corpus_tokens)

    def search(
        self, query: str, top_k: int = 5, k_rrf: int = 60
    ) -> List[TranscriptSearchMatch]:
        """Execute hybrid search using Reciprocal Rank Fusion."""
        if not self.chunks:
            return []

        num_docs = len(self.chunks)
        effective_k = min(num_docs, max(top_k * 3, 10))

        # --- A. Dense / Cosine Similarity ---
        if self.embedder is not None:
            try:
                query_embed = np.array(
                    list(self.embedder.embed([query])), dtype=np.float32
                )[0]
                query_norm = np.linalg.norm(query_embed)
                query_embed = query_embed / max(query_norm, 1e-9)
                dense_scores = np.dot(self.embeddings, query_embed)
            except Exception:
                dense_scores = np.zeros(num_docs, dtype=np.float32)
        elif self.tfidf_fallback is not None:
            query_vec = self.tfidf_fallback.transform(query)
            dense_scores = np.dot(self.embeddings, query_vec)
        else:
            dense_scores = np.zeros(num_docs, dtype=np.float32)

        dense_ranked_indices = np.argsort(-dense_scores)
        dense_rank_map = {
            int(idx): rank for rank, idx in enumerate(dense_ranked_indices)
        }

        # --- B. Sparse BM25 Retrieval ---
        query_tokens = bm25s.tokenize([query], stopwords="en")
        bm25_docs, bm25_scores = self.bm25.retrieve(
            query_tokens, k=min(num_docs, effective_k)
        )

        bm25_rank_map = {}
        if len(bm25_docs) > 0:
            for rank, doc_idx in enumerate(bm25_docs[0]):
                bm25_rank_map[int(doc_idx)] = rank

        # --- C. Reciprocal Rank Fusion (RRF) ---
        fused: List[tuple[float, int]] = []
        for idx in range(num_docs):
            r_dense = dense_rank_map.get(idx, 9999)
            r_sparse = bm25_rank_map.get(idx, 9999)

            score_dense = 1.0 / (k_rrf + r_dense)
            score_sparse = (
                1.0 / (k_rrf + r_sparse) if idx in bm25_rank_map else 0.0
            )

            rrf_score = score_dense + score_sparse
            fused.append((rrf_score, idx))

        fused.sort(key=lambda x: x[0], reverse=True)

        # Normalize top score to 1.0 scale
        max_rrf = fused[0][0] if fused else 1.0

        matches: List[TranscriptSearchMatch] = []
        for rrf_score, idx in fused[:top_k]:
            chunk = self.chunks[idx]
            norm_score = round(rrf_score / max(max_rrf, 1e-9), 3)

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
