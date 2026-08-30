# YouTube Research MCP — Production-Grade Research Engine

[![CI](https://img.shields.io/badge/tests-121%2B%20passed-brightgreen.svg)](tests/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![FastMCP](https://img.shields.io/badge/MCP-FastMCP%202.0-orange.svg)](https://github.com/jlowin/fastmcp)
[![ChatGPT Compatible](https://img.shields.io/badge/ChatGPT-Streamable%20HTTP-green.svg)](https://platform.openai.com)

A high-performance, model-agnostic, zero-API-key **Model Context Protocol (MCP)** server that turns YouTube into a structured, verifiable knowledge base for AI agents with deterministic cross-lingual retrieval.

Designed specifically for AI pair programmers and reasoning models (ChatGPT, Claude, Gemini, Cursor, Codex, OpenCode).

---

## ⚡ Performance & In-Process Latency Benchmarks

Measured directly on Windows 11 / Python 3.11 with SQLite WAL Mode & FastMCP in-process execution:

### 1. In-Process Operation Latencies
| Operation | Fresh Latency (P50) | Cached Latency (P50) | Cached Latency (P95) | Concurrency (100 reqs) |
| :--- | :--- | :--- | :--- | :--- |
| **`youtube_search`** | **~7.4 ms** | **~7.1 ms** | **~7.8 ms** | **2.83 ms / req** |
| **`youtube_video` (Metadata)** | **~6.5 ms** | **~5.8 ms** | **~6.4 ms** | **2.10 ms / req** |
| **`youtube_transcript`** | **~8.0 ms** | **~6.5 ms** | **~7.7 ms** | **2.45 ms / req** |
| **`youtube_find_in_video` (Hybrid RRF)** | **~20.9 ms** | **~18.2 ms** | **~46.1 ms** | **6.10 ms / req** |

### 2. High-Concurrency Single-Flight Load Harness (Separated Workloads)
| Workload | Concurrency | P50 Latency | P95 Latency | P99 Latency | Throughput | Single-Flight Coalesced |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Cached Workload** | 10 reqs | 0.029 ms | 0.045 ms | 0.049 ms | 4,080 req/s | 0 (Direct Cache Hits) |
| **Cached Workload** | 50 reqs | 0.019 ms | 0.031 ms | 0.041 ms | 12,616 req/s | 0 (Direct Cache Hits) |
| **Cached Workload** | 100 reqs | 0.022 ms | 0.027 ms | 0.030 ms | 8,411 req/s | 0 (Direct Cache Hits) |
| **Fresh Retrieval Workload** | 10 reqs | 2.41 ms | 3.44 ms | 3.88 ms | 377 req/s | 9 coalesced (1 in-process execution) |
| **Fresh Retrieval Workload** | 50 reqs | 2.13 ms | 3.16 ms | 3.69 ms | 426 req/s | 49 coalesced (1 in-process execution) |
| **Fresh Retrieval Workload** | 100 reqs | 3.39 ms | 4.41 ms | 4.79 ms | 310 req/s | 99 coalesced (1 in-process execution) |

> [!NOTE]
> **Benchmark Transparency Notice**: The reported throughput numbers measure **in-process async single-flight coalescing and in-memory retrieval performance** (e.g. coalescing 100 concurrent AI agent queries onto a single execution to protect downstream systems). They do **NOT** represent raw/fresh YouTube HTTP request throughput. Real-world un-cached network requests to YouTube remain subject to standard network latency and YouTube's per-IP rate limits.

---

## 🚀 Key Architecture & Production Features

```
AI Agent (ChatGPT / Claude / Cursor / OpenCode)
   │
   ▼ (Streamable HTTP / stdio / SSE)
FastMCP Server (Port 8000)
   ├── Bounded LRU Retrieval Index Cache (MAX=100, TTL=1hr)
   ├── Metrics & Observability Collector (`youtube://health`, `/api/admin/metrics`)
   └── Pluggable Cache Layer (SQLite WAL / Redis / Memory with Negative Caching & Auto-Purge)
         │
         ▼
   SingleFlight Request Coalescer (Zero Cache Stampedes)
         │
         ▼
   Capability-Aware Circuit Breakers (CLOSED / OPEN / HALF_OPEN)
         ├── Search Capability
         ├── Metadata Capability
         └── Transcript Capability
         │
         ▼
   Multi-Tier Provider Routing
         ├── Tier 1: Direct InnerTube (Shared HTTP/2 Connection Pool) / yt-dlp (Anti-Bot Rotation)
         ├── Tier 2: yt-dlp Fallback Extraction / InnerTube Fallback
         └── Tier 3: Commercial Fallbacks (Supadata)
```

1. **Anti-Bot Client Rotation Engine**: Automatically rotates player clients across `android`, `ios`, `tv_embedded`, and `mweb` without cookies or API keys.
2. **Pluggable Caching Architecture**:
   - **SQLite**: Local SQLite WAL database with auto-pruning at `MAX_CACHE_ENTRIES` and TTL expiration.
   - **Redis**: Production Redis integration with connection pooling, secret masking, and universal Redis 5.x/6.x/7.x compatibility via RESP2 (`protocol=2`).
   - **Memory**: High-speed in-process thread-safe dictionary cache.
3. **Capability-Level Circuit Breaker**: State machine (`CLOSED` $\rightarrow$ `OPEN` $\rightarrow$ `HALF_OPEN` with 1-probe concurrency lock) tracked individually for search, metadata, and transcript capabilities.
4. **Single-Flight Request Coalescing**: Prevents cache stampedes by merging duplicate in-flight requests into a single upstream execution.
5. **Multilingual Unicode Tokenization**: Native token splitting across Hindi (Devanagari), CJK (Chinese, Japanese), Korean (Hangul), Arabic, Cyrillic, and Latin scripts.
6. **Hybrid Semantic Retrieval (In-Process)**: BM25s sparse retrieval fused via Reciprocal Rank Fusion (RRF) with dense vector embeddings / TF-IDF.
7. **Multi-Video Research & Evidence Clustering**: Autonomous cross-video discovery with source channel diversity (`max_videos_per_channel=2`) and near-duplicate claim clustering.
8. **Security & Production Hardening**:
   - Constant-time Admin API Key authentication (`X-Admin-Key` / `Authorization: Bearer <KEY>`).
   - Strict CORS origin validation for public and administrative endpoints.
   - Per-IP Token-Bucket rate limiting on REST endpoints.
   - Resource-safe query length and transcript segment bounding (`MAX_TRANSCRIPT_SEGMENTS`, `MAX_QUERY_LENGTH`).

---

## 🛠️ MCP Tools Overview

### 1. `youtube_search`
Searches YouTube videos with deterministic post-filtering for dates and languages.
- `query` (string, required)
- `max_results` (int, default: 5, max: 25)
- `language` (string, default: "en")
- `published_after` (ISO date string `YYYY-MM-DD`, optional)
- `published_before` (ISO date string `YYYY-MM-DD`, optional)

### 2. `youtube_video`
Retrieves video metadata, view counts, upload date, tags, and chapter markers.
- `video_id` (string, required): 11-char ID or YouTube URL.

### 3. `youtube_transcript`
Extracts spoken transcripts with timestamp deep links and explicit language provenance.
- `video_id` (string, required)
- `language` (string, default: "en")
- `fallback_language` (string, default: "en", or null to disable)
- `include_timestamps` (bool, default: True)
- `translate_to` (string, optional)

### 4. `youtube_find_in_video`
Pinpoints exact sections in long videos discussing a specific topic using hybrid RRF search.
- `video_id` (string, required)
- `query` (string, required)
- `max_results` (int, default: 5)
- `language` (string, default: "en")
- `fallback_language` (string, default: "en")

### 5. `youtube_research`
Multi-video research discovery across diverse channels with near-duplicate claim clustering.
- `query` (string, required)
- `depth` ("quick" = 2 videos, "standard" = 3 videos, "deep" = 5 videos)
- `max_videos_per_channel` (int, default: 2)
- `language` (string, default: "en")
- `fallback_language` (string, default: "en")
- `published_after` (ISO date string `YYYY-MM-DD`, optional)
- `published_before` (ISO date string `YYYY-MM-DD`, optional)

---

## 📦 Installation & Setup

### Local Setup
```bash
# Clone the repository
git clone https://github.com/Unknowmyt1M/youtube-research-mcp.git
cd youtube-research-mcp

# Install dependencies using uv (recommended)
uv sync

# Run the MCP Server locally over Streamable HTTP
uv run python -m youtube_research_mcp.server --transport http --port 8000
```

---

## 🚂 Public Cloud Deployment (Railway-First)

Deploy this server to **Railway**, **Render**, **Fly.io**, or **Docker** to expose a unified remote endpoint for all your AI agents and coding tools:

```
https://<your-production-domain>/mcp
```

### 1. One-Click Railway Deployment
1. Connect your GitHub repository to [Railway](https://railway.com).
2. Railway detects [`Dockerfile`](file:///d:/Projects/MCP/AI-Youtube/Dockerfile) and [`railway.json`](file:///d:/Projects/MCP/AI-Youtube/railway.json) automatically.
3. Configure Environment Variables (optional: `ADMIN_API_KEY`, `REDIS_URL`).
4. Railway automatically sets dynamic `$PORT` and routes container traffic.
5. In **Networking**, click **Generate Domain** (e.g. `https://youtube-mcp-production.up.railway.app`).
6. Verify Health: `GET https://<your-domain>/` (returns HTTP 200).

---

## 🤖 Remote & Local Client Configuration

Use your hosted endpoint `https://<your-domain>/mcp` across any MCP-compatible AI client:

### 1. OpenCode (`opencode.json` / `opencode.jsonc`)
```json
{
  "mcp": {
    "servers": {
      "youtube-research": {
        "type": "remote",
        "url": "https://<your-domain>/mcp"
      }
    }
  }
}
```

### 2. Cursor (`~/.cursor/mcp.json`)
```json
{
  "mcpServers": {
    "youtube-research": {
      "url": "https://<your-domain>/mcp"
    }
  }
}
```

### 3. VS Code / GitHub Copilot Agent Mode (`.vscode/mcp.json`)
```json
{
  "servers": {
    "youtube-research": {
      "type": "http",
      "url": "https://<your-domain>/mcp"
    }
  }
}
```

### 4. Cline & Roo Code (`cline_mcp_settings.json`)
```json
{
  "mcpServers": {
    "youtube-research": {
      "type": "streamableHttp",
      "url": "https://<your-domain>/mcp",
      "disabled": false,
      "autoApprove": []
    }
  }
}
```

### 5. Windsurf (`~/.codeium/windsurf/mcp_config.json`)
```json
{
  "mcpServers": {
    "youtube-research": {
      "serverUrl": "https://<your-domain>/mcp"
    }
  }
}
```

### 6. ChatGPT Custom MCP Connector
In ChatGPT Developer / Custom Actions Settings:
```
https://<your-domain>/mcp
```

### 7. Claude Desktop Local Mode (`claude_desktop_config.json`)
```json
{
  "mcpServers": {
    "youtube-research": {
      "command": "uv",
      "args": [
        "--directory",
        "/path/to/youtube-research-mcp",
        "run",
        "python",
        "-m",
        "youtube_research_mcp.server",
        "--transport",
        "stdio"
      ]
    }
  }
}
```

---

## 🧪 Testing & Evaluation
 
```bash
# Run full unit and integration test suite (121 tests)
uv run pytest -v

# Run deterministic retrieval evaluation benchmark (Recall@1, MRR, timestamp accuracy)
uv run python tests/evaluation/evaluate_retrieval.py

# Run real Redis integration tests (requires local or remote Redis)
uv run pytest tests/integration/test_redis_live.py -v

# Run reproducible high-concurrency load benchmark (10, 50, 100 concurrent reqs)
uv run python tests/benchmarks/test_load_harness.py

# Run latency and concurrency benchmarks
uv run pytest tests/benchmarks/test_latency.py -s
uv run pytest tests/benchmarks/test_concurrency_benchmarks.py -s
```

---

## 📄 License

MIT License. Free for open-source and commercial AI agent workflows.
