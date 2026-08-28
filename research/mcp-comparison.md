# MCP Server Architecture, FastMCP & In-Process Semantic Retrieval

## 1. FastMCP vs Low-Level Python MCP SDK

| Feature | FastMCP (PrefectHQ / FastMCP standard) | Official Python SDK Low-Level (`mcp.server.lowlevel`) |
| :--- | :--- | :--- |
| **Developer Experience** | High-level decorator-driven (`@mcp.tool()`) | Manual JSON-RPC request dispatcher boilerplate |
| **Schema Generation** | Automatic Pydantic model $\rightarrow$ JSON Schema | Manual JSON schema construction |
| **Context & Progress** | Built-in `fastmcp.Context` for real-time logs & progress | Manual transport plumbing |
| **Transports** | `stdio` + HTTP / SSE streaming supported | Manual adapter setup required |
| **Selection** | **Selected Framework for this project** | Not recommended for rapid production agent tools |

---

## 2. The Multi-Hour Video Problem & Hybrid In-Process Retrieval

### The Context Blowout Problem:
A 2-hour podcast (e.g. Lex Fridman, Huberman Lab) contains ~35,000 words (~45,000 tokens).
Existing naive YouTube MCP servers dump the entire raw transcript into the agent context, leading to:
- Context limit blowout
- High LLM inference latency & token cost
- Needle-in-a-haystack attention degradation

### Solution: Zero-Dependency In-Process Hybrid Search (Dense Vector + Sparse BM25)
Instead of forcing the user to spin up Docker containers for Qdrant/Chroma or downloading 2GB PyTorch models:

```
Raw Subtitle Timed Events (json3)
       │
       ▼
Timestamp-Aware Semantic Chunker (150-250 words)
- Preserves start_time & generates clickable ?t=XXs deep links
- Merges natural sentence boundaries
       │
       ├──────────────────────────────────────────┐
       ▼                                          ▼
Dense Embeddings                             Sparse Lexical Index
(FastEmbed ONNX bge-small-en-v1.5, ~50MB)    (bm25s SciPy sparse matrix)
       │                                          │
       └──────────────────┬───────────────────────┘
                          ▼
             Reciprocal Rank Fusion (RRF)
     RRF_Score = 1/(60 + rank_dense) + 1/(60 + rank_bm25)
                          ▼
            Top-K Pinpoint Citations & Quotes
         (e.g., 300 words returned in < 200ms)
```

---

## 3. High-Performance Caching Architecture

### SQLite WAL Mode Cache:
- `PRAGMA journal_mode = WAL;` (Concurrent reads while writes execute)
- `PRAGMA synchronous = NORMAL;` (10x write speedup)
- `PRAGMA cache_size = -32000;` (32MB RAM page cache)
- `PRAGMA mmap_size = 268435456;` (256MB memory-mapped zero-copy I/O)

### Cache TTL Strategy:
- **Search Queries**: 12 Hours TTL
- **Video Metadata & Chapters**: 7 Days TTL
- **Transcripts & Chunks**: 60 Days TTL (Transcripts are immutable historical records)
- **Multi-Video Research Syntheses**: 24 Hours TTL
