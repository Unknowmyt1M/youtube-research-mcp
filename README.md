# ⚡ YouTube Research MCP Server

> **Give any MCP-compatible AI agent fast, reliable, structured access to YouTube as a research and knowledge source — with zero API keys required.**

---

## 🎯 Features

* 🚀 **Zero User API Keys Required**: Works out-of-the-box using direct InnerTube HTTP/2 API and resilient in-process `yt-dlp` extractors.
* ⚡ **Ultra-Low Latency & High Throughput**: Sub-2ms cached responses, sub-200ms fresh searches.
* 🧠 **Hybrid Semantic Retrieval (RRF)**: In-process dense vector + BM25s sparse lexical search locates exact 2-minute sections in 3-hour videos in ~10ms.
* 🕒 **Exact Timestamp Deep Links**: Generates clickable `https://youtu.be/{id}?t={seconds}` URLs for every quote and chunk.
* 🌐 **On-The-Fly Instant Translation**: Translate video transcripts into any language using YouTube's timedtext translation engine.
* 🗄️ **High-Performance SQLite Cache**: Persistent WAL-mode database with automatic TTL (12h search, 7d metadata, 60d transcripts).
* 🛡️ **Failover Provider Router**: Automatic failover (Tier 1: InnerTube `ANDROID`/`TV_EMBEDDED` $\rightarrow$ Tier 2: `yt-dlp` $\rightarrow$ Tier 3: Commercial fallback) with circuit breaking and rate limiting.
* 🤖 **Model Agnostic**: Works with Claude Desktop, Cursor, Cline, OpenClaw, Hermes Agent, Codex, Gemini CLI, and all MCP hosts.

---

## 🏗️ Architecture

```text
                    AI Agent (Claude / Cursor / Gemini)
                                   │
                                   │ JSON-RPC (stdio / SSE)
                                   ▼
                    ┌─────────────────────────────┐
                    │    YouTube Research MCP     │
                    └──────────────┬──────────────┘
                                   │
             ┌─────────────────────┼─────────────────────┐
             ▼                     ▼                     ▼
      youtube_search         youtube_video      youtube_transcript
             │                     │                     │
             └─────────────────────┼─────────────────────┘
                                   │
                                   ▼
                    ┌─────────────────────────────┐
                    │ High-Speed SQLite WAL Cache │
                    └──────────────┬──────────────┘
                                   │ (Cache Miss)
                                   ▼
                    ┌─────────────────────────────┐
                    │       Provider Router       │
                    └──────────────┬──────────────┘
                                   │
      ┌────────────────────────────┼────────────────────────────┐
      ▼                            ▼                            ▼
Tier 1: InnerTube           Tier 2: yt-dlp             Tier 3: Fallback
(Android/TV HTTP/2)         (In-Process Flat)          (Supadata/TranscriptAPI)
                                   │
                                   ▼
                    ┌─────────────────────────────┐
                    │  Timestamp-Aware Chunker    │
                    └──────────────┬──────────────┘
                                   │
                                   ▼
                    ┌─────────────────────────────┐
                    │   Hybrid RRF Search Engine  │
                    │   (Dense Vector + BM25s)    │
                    └──────────────┬──────────────┘
                                   │
                                   ▼
                    ┌─────────────────────────────┐
                    │ Timestamped Source Evidence │
                    │   "https://youtu.be/..?t=42"│
                    └─────────────────────────────┘
```

---

## 📊 Latency Benchmarks

Measured on live YouTube network responses and local cache:

| Operation | Fresh (P50) | Cached (P50) | Cache Hit Latency (P95) |
| :--- | :--- | :--- | :--- |
| **Search (`youtube_search`)** | ~1800 ms | **1.56 ms** ⚡ | **1.70 ms** |
| **Metadata (`youtube_video`)** | ~350 ms | **1.32 ms** ⚡ | **1.65 ms** |
| **Transcript (`youtube_transcript`)** | ~1500 ms | **2.14 ms** ⚡ | **2.36 ms** |
| **Hybrid In-Video Search (`youtube_find_in_video`)** | **10.49 ms** ⚡ | **10.49 ms** | **52.70 ms** |

---

## 🛠️ MCP Tools Overview

### 1. `youtube_search`
Search YouTube for videos matching a query with structured metadata and relevance ranking.
```json
{
  "query": "quantum computing breakthroughs 2026",
  "max_results": 5,
  "language": "en"
}
```

### 2. `youtube_video`
Retrieve complete metadata, view statistics, duration, and table-of-contents chapters.
```json
{
  "video_id": "dQw4w9WgXcQ"
}
```

### 3. `youtube_transcript`
Extract timestamped spoken transcript segments or clean continuous dialogue.
```json
{
  "video_id": "dQw4w9WgXcQ",
  "language": "en",
  "include_timestamps": true,
  "translate_to": "es"
}
```

### 4. `youtube_find_in_video`
Pinpoint exact sections and timestamps in long videos where a topic is discussed.
```json
{
  "video_id": "dQw4w9WgXcQ",
  "query": "never gonna give you up",
  "max_results": 3
}
```
**Output Example:**
```json
{
  "time_range": "00:42 - 01:15",
  "relevance_score": 0.94,
  "text": "Never gonna give you up, never gonna let you down...",
  "url": "https://youtu.be/dQw4w9WgXcQ?t=42"
}
```

### 5. `youtube_research`
Autonomous multi-video research. Discovers videos, extracts transcripts concurrently, performs semantic search, and aggregates timestamped citations.
```json
{
  "query": "How are AI coding agents evolving in 2026?",
  "max_videos": 5,
  "depth": "standard"
}
```

---

## 📦 Installation & Setup

### Option 1: Using `uv` (Recommended)
```bash
# Clone the repository
git clone https://github.com/your-username/youtube-research-mcp.git
cd youtube-research-mcp

# Create environment and install dependencies
uv venv
uv pip install -e .
```

### Option 2: Docker
```bash
docker build -t youtube-research-mcp .
docker run -i --rm -p 8000:8000 youtube-research-mcp
```

---

## 🔌 MCP Client Configuration

### Claude Desktop (`claude_desktop_config.json`)
```json
{
  "mcpServers": {
    "youtube-research": {
      "command": "uv",
      "args": [
        "--directory",
        "d:/Projects/MCP/AI-Youtube",
        "run",
        "youtube-research-mcp"
      ]
    }
  }
}
```

### Cursor (`.cursor/mcp.json`)
```json
{
  "mcpServers": {
    "youtube-research": {
      "command": "uv",
      "args": [
        "--directory",
        "d:/Projects/MCP/AI-Youtube",
        "run",
        "youtube-research-mcp"
      ]
    }
  }
}
```

---

## 🧪 Running Tests

```bash
# Run unit tests
pytest tests/unit -v

# Run integration tests (live YouTube endpoints)
pytest tests/integration -v

# Run latency benchmark suite
pytest tests/benchmarks/test_latency.py -s
```

---

## ⚖️ Legal & Ethical Considerations

* **Research & Transformative Fair Use**: This tool extracts public captions and video metadata for indexing, summarization, and research retrieval.
* **No Offline Video/Audio Redistribution**: The tool does not download, redistribute, or bypass access controls for copyrighted audio/video streams.
* **Attribution**: All citations preserve original creator channel names, video titles, and timestamped canonical YouTube deep links.

---

## 📄 License

MIT License. Copyright (c) 2026 Darko & Antigravity.
