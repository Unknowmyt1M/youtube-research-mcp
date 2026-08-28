# Architecture Decision Record (ADR): YouTube Research MCP

## 1. System Architecture Diagram

```
                              ┌─────────────────────────────┐
                              │    AI Agent / MCP Client    │
                              │  (Claude, Cursor, Gemini)   │
                              └──────────────┬──────────────┘
                                             │ JSON-RPC (stdio / SSE)
                                             ▼
                              ┌─────────────────────────────┐
                              │    YouTube Research MCP     │
                              │     (FastMCP Framework)     │
                              └──────────────┬──────────────┘
                                             │
                      ┌──────────────────────┼──────────────────────┐
                      ▼                      ▼                      ▼
               ┌─────────────┐        ┌─────────────┐        ┌─────────────┐
               │   Search    │        │  Metadata   │        │ Transcript  │
               │   Service   │        │   Service   │        │   Service   │
               └──────┬──────┘        └──────┬──────┘        └──────┬──────┘
                      │                      │                      │
                      └──────────────────────┼──────────────────────┘
                                             ▼
                              ┌─────────────────────────────┐
                              │   High-Speed SQLite Cache   │
                              │   (WAL Mode + 60-Day TTL)   │
                              └──────────────┬──────────────┘
                                             │ (Cache Miss)
                                             ▼
                              ┌─────────────────────────────┐
                              │       Provider Router       │
                              └──────────────┬──────────────┘
                                             │
             ┌───────────────────────────────┼───────────────────────────────┐
             ▼                               ▼                               ▼
     ┌───────────────┐               ┌───────────────┐               ┌───────────────┐
     │    Tier 1     │               │    Tier 2     │               │    Tier 3     │
     │Direct InnerTube│              │    yt-dlp     │               │  Commercial   │
     │(ANDROID/TV/WEB)│              │  (In-Process) │               │   Fallback    │
     └───────────────┘               └───────────────┘               └───────────────┘
                                             │
                                             ▼
                              ┌─────────────────────────────┐
                              │ Timestamp-Aware Chunker     │
                              └──────────────┬──────────────┘
                                             │
                                             ▼
                              ┌─────────────────────────────┐
                              │ Hybrid Semantic Engine      │
                              │ (FastEmbed ONNX + BM25s RRF)│
                              └──────────────┬──────────────┘
                                             │
                                             ▼
                              ┌─────────────────────────────┐
                              │   Evidence & Source Graph   │
                              │ (Precise deep links ?t=XXs) │
                              └─────────────────────────────┘
```

---

## 2. Core Architectural Decisions

### ADR 1: API-Keyless First Experience
- **Decision**: Out of the box, the server operates without requiring users to configure Google Data API keys or pay for commercial proxy tokens.
- **Why**: Eliminates onboarding friction. Zero quota costs for standard searches and transcript lookups.
- **Alternative Considered**: Official YouTube Data API v3.
- **Rejected Because**: 100 quota units per search (capped at 100 searches/day free) and inability to download arbitrary 3rd-party captions.
- **Fallback**: Direct InnerTube HTTP/2 (`ANDROID` client context) $\rightarrow$ in-process `yt-dlp` extractor $\rightarrow$ optional commercial API key if configured by server admin.

### ADR 2: FastMCP Framework for MCP Transport
- **Decision**: Build on `FastMCP` (standard Python MCP server framework).
- **Why**: Type-safe Pydantic tool parameters, automatic JSON Schema generation, native `stdio` and HTTP transports, zero boilerplate.
- **Alternative Considered**: Low-level `mcp.server.lowlevel`.
- **Rejected Because**: High protocol plumbing overhead.

### ADR 3: In-Process Hybrid Search (FastEmbed ONNX + BM25s RRF)
- **Decision**: Perform semantic chunk retrieval in-process using `fastembed` (`BAAI/bge-small-en-v1.5` ONNX runtime, ~50MB RAM) fused with `bm25s` via Reciprocal Rank Fusion.
- **Why**: Zero external database containers (no Qdrant/Chroma/Pinecone needed), runs on standard CPU in < 200ms, saves 95%+ LLM context tokens on long videos.
- **Alternative Considered**: Heavy PyTorch `sentence-transformers` or remote vector databases.
- **Rejected Because**: 2GB+ disk weight, slow startup times, and complex operational requirements.

### ADR 4: SQLite WAL Caching with Safe Data Retention
- **Decision**: Use local SQLite in Write-Ahead-Logging mode (`PRAGMA journal_mode = WAL`) with strict TTL expiration.
- **Why**: Sub-millisecond reads, zero external daemon requirements (Redis optional for distributed multi-worker deployments), fully compliant with data retention limits.

### ADR 5: Granular, Composable MCP Tool Set
- **V1 Core Tools**:
  1. `youtube_search`: Keyword search with filters & ranking.
  2. `youtube_video`: Rich video metadata & chapter breakdowns.
  3. `youtube_transcript`: Timestamp-preserving raw or formatted transcript.
  4. `youtube_find_in_video`: Pinpoint hybrid semantic search within a single video with deep links (`?t=XXs`).
- **V2 Research Engine Tool**:
  5. `youtube_research`: Autonomous multi-video discovery, parallel transcript ingestion, cross-video semantic retrieval, and timestamped evidence synthesis.
