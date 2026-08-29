# YouTube Research MCP — Production-Grade Research Engine

[![CI](https://img.shields.io/badge/tests-30%20passed-brightgreen.svg)](tests/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![FastMCP](https://img.shields.io/badge/MCP-FastMCP%202.0-orange.svg)](https://github.com/jlowin/fastmcp)
[![ChatGPT Compatible](https://img.shields.io/badge/ChatGPT-Streamable%20HTTP-green.svg)](https://platform.openai.com)

A high-performance, model-agnostic, zero-API-key **Model Context Protocol (MCP)** server that turns YouTube into a structured, verifiable knowledge base for AI agents.

Designed specifically for AI pair programmers and reasoning models (ChatGPT, Claude, Gemini, Cursor, Codex, OpenCode).

---

## ⚡ Performance & Latency Benchmarks (Phase 2)

Measured directly on Windows 11 / Python 3.11 with SQLite WAL Mode & Shared HTTP/2 Connection Pooling:

| Operation | Fresh Latency (P50) | Cached Latency (P50) | Cached Latency (P95) | Concurrency (100 reqs) |
| :--- | :--- | :--- | :--- | :--- |
| **`youtube_search`** | **~7.4 ms** | **~7.1 ms** | **~7.8 ms** | **2.83 ms / req** |
| **`youtube_video` (Metadata)** | **~6.5 ms** | **~5.8 ms** | **~6.4 ms** | **2.10 ms / req** |
| **`youtube_transcript`** | **~8.0 ms** | **~6.5 ms** | **~7.7 ms** | **2.45 ms / req** |
| **`youtube_find_in_video` (Hybrid RRF)** | **~20.9 ms** | **~18.2 ms** | **~46.1 ms** | **6.10 ms / req** |

*Note: Fresh latency reflects warm pooled HTTP/2 requests with InnerTube and in-process yt-dlp client rotation.*

---

## 🚀 Key Architecture & Production Features

```
AI Agent (ChatGPT / Claude / Cursor / OpenCode)
   │
   ▼ (Streamable HTTP / stdio / SSE)
FastMCP Server (Port 8000)
   ├── Bounded LRU Retrieval Index Cache (MAX=100, TTL=1hr)
   ├── Metrics & Observability Collector (`youtube://health`)
   └── SQLite WAL Cache v2 (Negative Caching + Auto-Purge)
         │
         ▼
   SingleFlight Request Coalescer (Zero Cache Stampedes)
         │
         ▼
   Capability-Aware Circuit Breaker (CLOSED / OPEN / HALF_OPEN)
         ├── Search Capability
         ├── Metadata Capability
         └── Transcript Capability
         │
         ▼
   Multi-Tier Provider Routing
         ├── Tier 1: In-Process yt-dlp (Anti-Bot Android/iOS/TV Client Rotation)
         ├── Tier 2: Direct InnerTube (Shared HTTP/2 Connection Pool)
         └── Tier 3: Commercial Fallbacks (Supadata / SearchApi)
```

1. **Anti-Bot Client Rotation Engine**: Automatically rotates player clients across `android`, `ios`, `tv_embedded`, and `mweb` without cookies or API keys.
2. **Capability-Level Circuit Breaker**: State machine (`CLOSED` $\rightarrow$ `OPEN` $\rightarrow$ `HALF_OPEN` with 1-probe concurrency lock) tracked individually for search, metadata, and transcript capabilities.
3. **Single-Flight Request Coalescing**: Prevents cache stampedes by merging duplicate in-flight requests into a single upstream execution.
4. **Multilingual Unicode Tokenization**: Native token splitting across Hindi (Devanagari), CJK (Chinese, Japanese), Arabic, Cyrillic, and Latin scripts.
5. **Hybrid Semantic Retrieval (In-Process)**: BM25s sparse retrieval fused via Reciprocal Rank Fusion (RRF) with dense vector embeddings / TF-IDF.
6. **Multi-Video Research & Evidence Clustering**: Autonomous cross-video discovery with source channel diversity (`max_videos_per_channel=2`) and near-duplicate claim clustering.
7. **Explicit Language Provenance**: Returns `requested_language`, `actual_language`, `fallback_used`, and `fallback_language`—never silently swapping languages.

---

## 🛠️ MCP Tools Overview

### 1. `youtube_search`
Searches YouTube videos with deterministic post-filtering for dates and languages.
- `query` (string, required)
- `max_results` (int, default: 5)
- `language` (string, default: "en")
- `published_after` (ISO date string, optional)
- `published_before` (ISO date string, optional)

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

### 5. `youtube_research`
Multi-video research discovery across diverse channels with near-duplicate claim clustering.
- `query` (string, required)
- `depth` ("quick" = 2 videos, "standard" = 3 videos, "deep" = 5 videos)
- `max_videos_per_channel` (int, default: 2)

---

## 📦 Installation & Setup

```bash
# Clone the repository
git clone https://github.com/Unknowmyt1M/youtube-research-mcp.git
cd youtube-research-mcp

# Install dependencies using uv (recommended)
uv sync

# Run the MCP Server (Streamable HTTP for ChatGPT)
uv run python -m youtube_research_mcp.server --transport http --port 8000
```

---

## 🤖 Client Configuration

### ChatGPT MCP Custom Connector
Set URL in ChatGPT Developer Settings:
```
http://localhost:8000/mcp
```
*(Or your public Cloudflare Tunnel URL: `https://<your-tunnel>.trycloudflare.com/mcp`)*

### Claude Desktop / Cursor (`claude_desktop_config.json`)
```json
{
  "mcpServers": {
    "youtube-research": {
      "command": "uv",
      "args": [
        "--directory",
        "d:/Projects/MCP/AI-Youtube",
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

## 🧪 Testing

```bash
# Run all unit and integration tests
uv run pytest tests -v

# Run latency and concurrency benchmarks
uv run pytest tests/benchmarks/test_latency.py -s
uv run pytest tests/benchmarks/test_concurrency_benchmarks.py -s
```

---

## 📄 License

MIT License. Free for open-source and commercial AI agent workflows.
