import { DocCategory } from '../types/docs';

export const DOCS_CATEGORIES: DocCategory[] = [
  {
    id: 'introduction',
    title: 'Introduction',
    icon: 'Compass',
    pages: [
      {
        id: 'what-is-nexora',
        title: 'What is Nexora?',
        category: 'Introduction',
        description: 'Discover Nexora — the AI-powered video intelligence platform and Model Context Protocol (MCP) server for developers and reasoning agents.',
        badge: 'Core',
        updatedAt: '2026-08-30',
        sections: [
          {
            id: 'overview',
            title: 'Overview',
            content: `**Nexora** is an enterprise-grade video intelligence engine and Model Context Protocol (MCP) server. It allows AI agents, reasoning models (ChatGPT, Claude, Gemini, Cursor, OpenCode), and developers to search, inspect, transcribe, semantically pinpoint, and synthesize knowledge from video content with **zero API keys** and **deterministic verification**.

Our mission is captured in our tagline:
> **"Understand Everything. Instantly."**

While traditional web search engines only see video titles and thumbnails, Nexora dives deep into the spoken dialogue, timed captions, chapter markers, and contextual concepts.`,
            callouts: [
              {
                type: 'important',
                title: 'Live Remote MCP Endpoint',
                content: 'Nexora is publicly deployed on Railway over Streamable HTTP at `https://youtube-research-mcp-production.up.railway.app/mcp`. You can connect your AI agent immediately without installing local binaries.',
              },
            ],
          },
          {
            id: 'key-capabilities',
            title: 'Key Capabilities',
            content: `Nexora provides five core superpowers out of the box:

1. **Zero-API-Key Video Discovery**: Fast, resilient YouTube search with date and language filtering powered by multi-tier InnerTube rotation.
2. **Deep Metadata & Chapter Extraction**: Instant extraction of views, upload timestamps, video tags, and structured chapters.
3. **Full Timestamped Transcripts**: Multilingual caption extraction with automatic language fallbacks and timed segment alignment.
4. **In-Process Semantic Pinpointing (youtube_find_in_video)**: Hybrid Reciprocal Rank Fusion (FastEmbed dense vectors + BM25s sparse lexical search) to pinpoint exact 2-minute video segments and generate deep-link timestamp URLs (?t=842s).
5. **Autonomous Multi-Video Research (youtube_research)**: Cross-video synthesis engine that investigates a research question across multiple channels, extracts verified quotes, and generates structured citations.`,
          },
          {
            id: 'positioning-and-architecture',
            title: 'Branding & Migration Notice',
            content: `Nexora was originally developed under the open-source technical identifier **youtube-research-mcp**. 

During our current Phase 1 branding migration, youtube-research-mcp is maintained as a **100% backwards-compatible legacy identifier** across package names, CLI commands, and internal module paths. All existing client configurations remain fully functional without changes.`,
          },
        ],
        relatedPages: [
          { id: 'quickstart', title: 'Quick Start', category: 'Getting Started' },
          { id: 'core-concepts', title: 'Core Concepts', category: 'Introduction' },
          { id: 'tool-youtube-find-in-video', title: 'youtube_find_in_video', category: 'MCP' },
        ],
      },
      {
        id: 'why-nexora',
        title: 'Why Nexora?',
        category: 'Introduction',
        description: 'Understand the engineering decisions that make Nexora dramatically faster, more resilient, and more cost-effective than traditional video scrapers.',
        updatedAt: '2026-08-30',
        sections: [
          {
            id: 'problem-statement',
            title: 'The Problem with Existing Solutions',
            content: `Developers and AI agent creators trying to extract intelligence from video usually hit three major roadblocks:

* **Official YouTube Data API Quota Limits**: The YouTube Data API v3 enforces a strict default 10,000 unit daily quota. A single search call costs 100 units (allowing only 100 searches/day), and transcript extraction is not even supported through Data API v3.
* **Fragile Web Scraping**: Standard DOM scrapers frequently break when YouTube alters its web frontend classes, causing critical runtime crashes in AI agent workflows.
* **Token Bloat & Context Exhaustion**: Dumping raw 2-hour transcripts into an LLM context window burns 30,000+ tokens per query, slows down response times, and costs significant API credits.`,
          },
          {
            id: 'nexora-solution',
            title: 'How Nexora Solves This',
            content: `Nexora was architected from the ground up for high-concurrency AI pair programming and research:

| Feature | Generic Scrapers / Official API | Nexora Intelligence Platform |
| :--- | :--- | :--- |
| **API Key Required** | Yes (Strict daily quota) | **No** (Zero keys needed for search & transcripts) |
| **Transcript Latency** | 2,500 ms – 5,000 ms | **~8.0 ms (cached) / ~1.8s (fresh)** |
| **Semantic Pinpointing** | None (Raw text dump) | **In-process BM25s + FastEmbed Vector RRF** |
| **Cache Stampede Protection** | None (Redundant requests hit server) | **Async SingleFlight Request Coalescing** |
| **Circuit Breakers** | None (Fails silently or hangs) | **Capability-Level State Machine (Search/Meta/Transcript)** |
| **Multi-Video Synthesis** | Manual agent orchestration | **Native youtube_research clustering engine** |`,
          },
        ],
      },
      {
        id: 'core-concepts',
        title: 'Core Concepts',
        category: 'Introduction',
        description: 'Master the fundamental concepts behind Nexora: Hybrid RRF, SingleFlight coalescing, and Streamable HTTP MCP.',
        updatedAt: '2026-08-30',
        sections: [
          {
            id: 'hybrid-rrf',
            title: 'Hybrid Reciprocal Rank Fusion (RRF)',
            content: `When searching inside long videos, pure keyword search fails on paraphrased concepts, while pure dense vector embeddings often miss specific technical jargon (e.g. function names, error codes, version numbers).

Nexora solves this by executing a **two-stage Hybrid RRF pipeline**:
1. **Lexical Sparse Search (BM25s)**: Ultra-fast in-memory BM25 indexing with multilingual Unicode tokenizer (Devanagari, CJK, Hangul, Latin).
2. **Dense Semantic Embeddings (FastEmbed)**: In-process ONNX-optimized transformer embeddings.
3. **Reciprocal Rank Fusion**: Merges both rank lists using Reciprocal Rank Fusion with k=60 to guarantee deterministic, high-precision passage discovery.`,
          },
          {
            id: 'singleflight-coalescing',
            title: 'SingleFlight Coalescing',
            content: `In multi-agent environments, multiple AI threads frequently query the same video transcript simultaneously. Without protection, this causes a **cache stampede** that can trigger upstream YouTube bot checks.

Nexora implements **SingleFlight Mutex Locking**:
* If 50 concurrent requests ask for the transcript of video zjkBMFhNj_g, exactly **1 request** fetches upstream data.
* The remaining 49 requests wait asynchronously on an internal Python asyncio.Event and receive the identical result simultaneously.`,
          },
        ],
      },
      {
        id: 'architecture-overview',
        title: 'Architecture',
        category: 'Introduction',
        description: 'Explore the high-level system components, request flow, and resilience layers powering Nexora.',
        updatedAt: '2026-08-30',
        sections: [
          {
            id: 'system-diagram',
            title: 'System Architecture',
            content: `\`\`\`text
AI Client (ChatGPT / Claude / Cursor / OpenCode)
   │
   ▼ (Streamable HTTP / SSE / stdio)
Nexora MCP Server (Port 8000 / Dynamic Cloud Port)
   ├── StreamableHTTPSessionManager (Session Tracking & Multiplexing)
   ├── Token-Bucket Rate Limiter (10 RPS / 20 Burst)
   ├── Metrics & Telemetry Engine (youtube://health, /api/admin/metrics)
   └── Pluggable Cache Layer (SQLite WAL / Redis / In-Memory with TTL)
         │
         ▼
   SingleFlight Request Coalescer (Zero Cache Stampedes)
         │
         ▼
   Capability Circuit Breakers (Search / Metadata / Transcript)
         │
         ▼
   Multi-Tier Provider Pipeline
         ├── Tier 1: Direct InnerTube (Shared HTTP/2 Pool) & Anti-Bot Client Rotation
         ├── Tier 2: yt-dlp Subprocess & Multi-Context Fallback
         └── Tier 3: Isolated Commercial Fallbacks (Supadata/SearchApi)
\`\`\``,
          },
        ],
      },
    ],
  },
  {
    id: 'getting-started',
    title: 'Getting Started',
    icon: 'Zap',
    pages: [
      {
        id: 'quickstart',
        title: 'Quick Start',
        category: 'Getting Started',
        description: 'Connect your AI agent or IDE to the live Nexora MCP server in under 60 seconds.',
        badge: 'Popular',
        updatedAt: '2026-08-30',
        sections: [
          {
            id: 'endpoint-details',
            title: '1. Production Endpoint',
            content: `You can connect directly to Nexora without installing Python, Docker, or managing API keys.

* **Live URL**: https://youtube-research-mcp-production.up.railway.app/mcp
* **Transport**: Streamable HTTP / Server-Sent Events (SSE)
* **Protocol Version**: mcp-2024-11-05`,
          },
          {
            id: 'client-configs',
            title: '2. Client Configuration Examples',
            content: 'Copy and paste the configuration into your preferred AI agent environment:',
            codeTabs: [
              {
                language: 'json',
                label: 'Cursor',
                filename: '.cursor/mcp.json',
                code: `{\n  "mcpServers": {\n    "nexora": {\n      "url": "https://youtube-research-mcp-production.up.railway.app/mcp"\n    }\n  }\n}`,
              },
              {
                language: 'json',
                label: 'Claude Desktop',
                filename: 'claude_desktop_config.json',
                code: `{\n  "mcpServers": {\n    "nexora": {\n      "url": "https://youtube-research-mcp-production.up.railway.app/mcp"\n    }\n  }\n}`,
              },
              {
                language: 'json',
                label: 'OpenCode',
                filename: 'opencode.json',
                code: `{\n  "mcp": {\n    "servers": {\n      "nexora": {\n        "type": "remote",\n        "url": "https://youtube-research-mcp-production.up.railway.app/mcp"\n      }\n    }\n  }\n}`,
              },
              {
                language: 'json',
                label: 'VS Code / Copilot',
                filename: '.vscode/mcp.json',
                code: `{\n  "servers": {\n    "nexora": {\n      "type": "sse",\n      "url": "https://youtube-research-mcp-production.up.railway.app/mcp"\n    }\n  }\n}`,
              },
            ],
          },
        ],
      },
      {
        id: 'first-mcp-request',
        title: 'Your First MCP Request',
        category: 'Getting Started',
        description: 'Step-by-step walkthrough of invoking Nexora tools and inspecting structured responses.',
        updatedAt: '2026-08-30',
        sections: [
          {
            id: 'example-query',
            title: 'Calling youtube_find_in_video',
            content: `Once connected to Nexora, your AI client can directly search inside any YouTube video using natural language.

Try asking your AI agent:
> "Use Nexora to find where 3Blue1Brown explains why basis vectors i-hat and j-hat describe a 2D matrix transformation in video kYB8IZa5AuE."`,
            codeTabs: [
              {
                language: 'json',
                label: 'Tool Call Request',
                code: `{\n  "jsonrpc": "2.0",\n  "id": 1,\n  "method": "tools/call",\n  "params": {\n    "name": "youtube_find_in_video",\n    "arguments": {\n      "video_id": "kYB8IZa5AuE",\n      "query": "where do basis vectors i-hat and j-hat land",\n      "max_results": 1\n    }\n  }\n}`,
              },
              {
                language: 'json',
                label: 'Tool Call Response',
                code: `{\n  "status": "success",\n  "video_id": "kYB8IZa5AuE",\n  "query": "where do basis vectors i-hat and j-hat land",\n  "total_matches": 1,\n  "matches": [\n    {\n      "chunk_id": "kYB8IZa5AuE_c005",\n      "time_range": "03:35 - 04:40",\n      "start_seconds": 215.48,\n      "end_seconds": 280.92,\n      "relevance_score": 1.0,\n      "text": "It turns out that you only need to record where the two basis vectors, i-hat and j-hat, each land, and everything else will follow from that...",\n      "url": "https://youtu.be/kYB8IZa5AuE?t=215",\n      "chapter_title": "package coordinates into 2x2 grid"\n    }\n  ]\n}`,
              },
            ],
          },
        ],
      },
      {
        id: 'auth-access',
        title: 'Authentication & Access',
        category: 'Getting Started',
        description: 'Understand public MCP tool access rules and admin API protection with ADMIN_API_KEY.',
        updatedAt: '2026-08-30',
        sections: [
          {
            id: 'auth-model',
            title: 'Authentication Model',
            content: `Nexora adopts a dual-tier access model:

1. **Public MCP Tools & Discovery (Zero Auth)**:
   * Endpoints: POST /mcp, POST /api/search, POST /api/video, POST /api/transcript, POST /api/find_in_video, POST /api/research.
   * Authentication: None required. Protected by a sliding Token Bucket rate limiter (10 RPS, 20 burst).
2. **Administrative Control Plane (ADMIN_API_KEY Required)**:
   * Endpoints: GET /api/admin/metrics, POST /api/admin/cache/clear, GET /api/admin/circuit-breakers.
   * Authentication: Pass header \`Authorization: Bearer <ADMIN_API_KEY>\` or \`X-Admin-Key: <ADMIN_API_KEY>\`.
   * Security: Verified via Python \`secrets.compare_digest\` for constant-time cryptographic protection against timing attacks.`,
          },
        ],
      },
    ],
  },
  {
    id: 'mcp-tools',
    title: 'MCP Tools Reference',
    icon: 'Wrench',
    pages: [
      {
        id: 'mcp-overview',
        title: 'MCP Overview',
        category: 'MCP',
        description: 'Understand how Nexora implements the Model Context Protocol 2024-11-05 standard over Streamable HTTP.',
        badge: 'Protocol',
        updatedAt: '2026-08-30',
        sections: [
          {
            id: 'protocol-spec',
            title: 'Protocol & Transports',
            content: `Nexora exposes full FastMCP 2.0 protocol compatibility:
* **Transport**: Streamable HTTP (default on Railway) / SSE / stdio.
* **Standard Methods**: \`initialize\`, \`tools/list\`, \`tools/call\`, \`resources/list\`, \`resources/read\`, \`ping\`.
* **Telemetry Resource**: \`youtube://health\` provides live cache hit ratios, active circuit breakers, and latency percentiles.`,
          },
        ],
      },
      {
        id: 'tool-youtube-search',
        title: 'youtube_search',
        category: 'MCP',
        description: 'Search YouTube for videos with deterministic post-filtering by date and language without API keys.',
        badge: 'Search',
        updatedAt: '2026-08-30',
        sections: [
          {
            id: 'purpose',
            title: 'Purpose & Description',
            content: `The youtube_search tool queries YouTube's InnerTube search endpoint using anti-bot client rotation. It extracts video metadata, channel details, duration, view counts, and published dates.`,
            params: [
              { name: 'query', type: 'string', required: true, description: 'Search keywords, topic, or question (max 500 characters).' },
              { name: 'max_results', type: 'integer', required: false, default: '5', description: 'Number of results to retrieve (1 to 25).' },
              { name: 'language', type: 'string', required: false, default: 'en', description: 'ISO 639-1 language code (e.g. en, hi, es, fr).' },
              { name: 'published_after', type: 'string', required: false, description: 'Filter videos uploaded after ISO date (YYYY-MM-DD).' },
              { name: 'published_before', type: 'string', required: false, description: 'Filter videos uploaded before ISO date (YYYY-MM-DD).' },
            ],
            codeTabs: [
              {
                language: 'json',
                label: 'MCP Tool Arguments',
                code: `{\n  "query": "Andrej Karpathy Intro to Large Language Models",\n  "max_results": 2\n}`,
              },
              {
                language: 'bash',
                label: 'cURL REST Equivalent',
                code: `curl -X POST https://youtube-research-mcp-production.up.railway.app/api/search \\\n  -H "Content-Type: application/json" \\\n  -d '{"query": "Andrej Karpathy Intro to Large Language Models", "max_results": 2}'`,
              },
            ],
          },
        ],
      },
      {
        id: 'tool-youtube-video',
        title: 'youtube_video',
        category: 'MCP',
        description: 'Fetch detailed video metadata, view counts, chapters, upload dates, tags, and caption availability.',
        badge: 'Metadata',
        updatedAt: '2026-08-30',
        sections: [
          {
            id: 'purpose',
            title: 'Purpose & Schema',
            content: `Retrieves complete technical metadata for any public YouTube video using 11-character video IDs or standard YouTube URLs.`,
            params: [
              { name: 'video_id', type: 'string', required: true, description: '11-character YouTube video ID or full URL (e.g. zjkBMFhNj_g or https://youtu.be/zjkBMFhNj_g).' },
            ],
            codeTabs: [
              {
                language: 'json',
                label: 'MCP Tool Arguments',
                code: `{\n  "video_id": "zjkBMFhNj_g"\n}`,
              },
              {
                language: 'json',
                label: 'Response Sample',
                code: `{\n  "video_id": "zjkBMFhNj_g",\n  "title": "[1hr Talk] Intro to Large Language Models",\n  "channel": "Andrej Karpathy",\n  "channel_id": "UCXUPKJO5MZQN11PqgIvyuvQ",\n  "duration_seconds": 3588,\n  "duration_formatted": "59m 48s",\n  "view_count": 4016153,\n  "caption_available": true,\n  "chapters": [\n    { "title": "LLM Training", "start_seconds": 455.0, "url": "https://youtu.be/zjkBMFhNj_g?t=455" },\n    { "title": "Finetuning", "start_seconds": 969.0, "url": "https://youtu.be/zjkBMFhNj_g?t=969" },\n    { "title": "LLM OS", "start_seconds": 2575.0, "url": "https://youtu.be/zjkBMFhNj_g?t=2575" }\n  ]\n}`,
              },
            ],
          },
        ],
      },
      {
        id: 'tool-youtube-transcript',
        title: 'youtube_transcript',
        category: 'MCP',
        description: 'Extract complete timed caption tracks with language fallbacks, translations, and word count telemetry.',
        badge: 'Transcript',
        updatedAt: '2026-08-30',
        sections: [
          {
            id: 'purpose',
            title: 'Purpose & Parameters',
            content: `Extracts timed dialogue segments without API keys. Uses dual-tier fallback between InnerTube timedtext and yt-dlp caption streams.`,
            params: [
              { name: 'video_id', type: 'string', required: true, description: '11-character video ID or YouTube URL.' },
              { name: 'language', type: 'string', required: false, default: 'en', description: 'Desired ISO language code (e.g. en, hi, es).' },
              { name: 'fallback_language', type: 'string', required: false, default: 'en', description: 'Language to fallback to if requested is unavailable.' },
              { name: 'translate_to', type: 'string', required: false, description: 'Optional target language for automated YouTube translation.' },
            ],
          },
        ],
      },
      {
        id: 'tool-youtube-find-in-video',
        title: 'youtube_find_in_video',
        category: 'MCP',
        description: 'Pinpoint exact spoken sections and deep-link timestamp URLs in a video using in-process Hybrid RRF search.',
        badge: 'Pinpoint',
        updatedAt: '2026-08-30',
        sections: [
          {
            id: 'purpose',
            title: 'In-Process Semantic Pinpointing',
            content: `This tool is strongly preferred over fetching full transcripts for videos longer than 10 minutes. Instead of burning 20,000+ LLM tokens reading a full podcast transcript, youtube_find_in_video runs local BM25s + vector fusion to return only the most relevant 2–3 minute chunks with exact timestamp deep links (?t=X).`,
            params: [
              { name: 'video_id', type: 'string', required: true, description: '11-character YouTube video ID or URL.' },
              { name: 'query', type: 'string', required: true, description: 'The specific concept, question, or phrase to locate.' },
              { name: 'max_results', type: 'integer', required: false, default: '5', description: 'Number of relevant chunks to retrieve (1 to 10).' },
              { name: 'language', type: 'string', required: false, default: 'en', description: 'Transcript language code.' },
            ],
          },
        ],
      },
      {
        id: 'tool-youtube-research',
        title: 'youtube_research',
        category: 'MCP',
        description: 'Autonomous multi-video research and evidence synthesis engine with channel diversity and quotation verification.',
        badge: 'Synthesis',
        updatedAt: '2026-08-30',
        sections: [
          {
            id: 'purpose',
            title: 'Multi-Video Knowledge Synthesis',
            content: `Orchestrates a comprehensive cross-video research investigation:
1. Searches YouTube for top relevant candidate videos.
2. Applies source diversity limits (max_videos_per_channel=2).
3. Concurrently retrieves transcripts and indexes chunks.
4. Ranks evidence quotes across all candidate videos.
5. Returns structured citations with timestamps and channel attributions.`,
            params: [
              { name: 'query', type: 'string', required: true, description: 'The overarching research question or topic.' },
              { name: 'depth', type: 'string', required: false, default: 'standard', description: 'Research depth: "quick" (2 videos) or "standard" (5 videos).' },
              { name: 'language', type: 'string', required: false, default: 'en', description: 'Search and transcript language filter.' },
            ],
          },
        ],
      },
    ],
  },
  {
    id: 'integrations',
    title: 'Integrations',
    icon: 'Layers',
    pages: [
      {
        id: 'integration-opencode',
        title: 'OpenCode',
        category: 'Integrations',
        description: 'Configure OpenCode to connect to Nexora remote Streamable HTTP MCP server.',
        updatedAt: '2026-08-30',
        sections: [
          {
            id: 'opencode-setup',
            title: 'Configuration File',
            content: 'Add the Nexora remote server to your `opencode.json` configuration:',
            codeTabs: [
              {
                language: 'json',
                label: 'opencode.json',
                code: `{\n  "mcp": {\n    "servers": {\n      "nexora": {\n        "type": "remote",\n        "url": "https://youtube-research-mcp-production.up.railway.app/mcp"\n      }\n    }\n  }\n}`,
              },
            ],
          },
        ],
      },
      {
        id: 'integration-claude',
        title: 'Claude Desktop',
        category: 'Integrations',
        description: 'Connect Claude Desktop to the live Nexora MCP server on macOS or Windows.',
        updatedAt: '2026-08-30',
        sections: [
          {
            id: 'claude-setup',
            title: 'Claude Desktop Configuration',
            content: 'Add to `claude_desktop_config.json`:',
            codeTabs: [
              {
                language: 'json',
                label: 'claude_desktop_config.json',
                code: `{\n  "mcpServers": {\n    "nexora": {\n      "url": "https://youtube-research-mcp-production.up.railway.app/mcp"\n    }\n  }\n}`,
              },
            ],
          },
        ],
      },
      {
        id: 'integration-cursor',
        title: 'Cursor',
        category: 'Integrations',
        description: 'Connect Cursor IDE to Nexora MCP for instant code and video intelligence in pair programming.',
        updatedAt: '2026-08-30',
        sections: [
          {
            id: 'cursor-setup',
            title: 'Cursor Project Config',
            content: 'Create `.cursor/mcp.json` in your workspace:',
            codeTabs: [
              {
                language: 'json',
                label: '.cursor/mcp.json',
                code: `{\n  "mcpServers": {\n    "nexora": {\n      "url": "https://youtube-research-mcp-production.up.railway.app/mcp"\n    }\n  }\n}`,
              },
            ],
          },
        ],
      },
      {
        id: 'integration-vscode',
        title: 'VS Code / Copilot',
        category: 'Integrations',
        description: 'Connect Visual Studio Code with GitHub Copilot Chat to Nexora MCP.',
        updatedAt: '2026-08-30',
        sections: [
          {
            id: 'vscode-setup',
            title: 'VS Code MCP Config',
            content: 'Add to `.vscode/mcp.json`:',
            codeTabs: [
              {
                language: 'json',
                label: '.vscode/mcp.json',
                code: `{\n  "servers": {\n    "nexora": {\n      "type": "sse",\n      "url": "https://youtube-research-mcp-production.up.railway.app/mcp"\n    }\n  }\n}`,
              },
            ],
          },
        ],
      },
      {
        id: 'integration-cline-roo-windsurf',
        title: 'Cline, Roo Code & Windsurf',
        category: 'Integrations',
        description: 'Connect autonomous agent extensions Cline, Roo Code, and Windsurf to Nexora.',
        updatedAt: '2026-08-30',
        sections: [
          {
            id: 'agent-setup',
            title: 'Agent MCP Setup',
            content: 'In your agent MCP settings UI or JSON config, enter:\n* **Server Name**: `nexora`\n* **Server Type**: `Remote / Streamable HTTP`\n* **Server URL**: `https://youtube-research-mcp-production.up.railway.app/mcp`',
          },
        ],
      },
    ],
  },
  {
    id: 'rest-api',
    title: 'REST API Reference',
    icon: 'Code2',
    pages: [
      {
        id: 'api-overview',
        title: 'API Overview',
        category: 'REST API',
        description: 'Inspect Nexora REST endpoints, OpenAPI specification, and authentication model.',
        updatedAt: '2026-08-30',
        sections: [
          {
            id: 'rest-endpoints',
            title: 'Base URL & Endpoints',
            content: `Base URL:
\`\`\`text
https://youtube-research-mcp-production.up.railway.app
\`\`\`

* GET / — Service metadata.
* GET /health — Cloud health check.
* GET /openapi.json — OpenAPI 3.1.0 JSON schema.
* POST /api/search — Video search.
* POST /api/video — Video metadata.
* POST /api/transcript — Timed captions extraction.
* POST /api/find_in_video — Semantic pinpointing.
* POST /api/research — Multi-video research.`,
          },
        ],
      },
      {
        id: 'api-search',
        title: 'POST /api/search',
        category: 'REST API',
        description: 'Search YouTube videos via REST API with date and language filtering.',
        updatedAt: '2026-08-30',
        sections: [
          {
            id: 'req-resp',
            title: 'Request & Response Example',
            codeTabs: [
              {
                language: 'bash',
                label: 'cURL',
                code: `curl -X POST https://youtube-research-mcp-production.up.railway.app/api/search \\\n  -H "Content-Type: application/json" \\\n  -d '{"query": "3blue1brown neural networks", "max_results": 2}'`,
              },
            ],
          },
        ],
      },
      {
        id: 'api-rate-limits',
        title: 'Rate Limits',
        category: 'REST API',
        description: 'Understand the Token Bucket rate limiter (10 RPS / 20 burst) and 429 backoff handling.',
        updatedAt: '2026-08-30',
        sections: [
          {
            id: 'limits-spec',
            title: 'Token Bucket Architecture',
            content: `Nexora enforces a thread-safe in-memory Token Bucket rate limiter across all public endpoints:
* **Refill Rate**: 10 requests per second (\`RATE_LIMIT_RPS=10\`).
* **Burst Capacity**: 20 requests (\`RATE_LIMIT_BURST=20\`).
* **Headers**: Every response includes \`X-RateLimit-Limit\` and \`X-RateLimit-Remaining\`.
* **429 Recovery**: On HTTP 429, back off for 1–2 seconds.`,
          },
        ],
      },
    ],
  },
  {
    id: 'self-hosting',
    title: 'Self Hosting',
    icon: 'Server',
    pages: [
      {
        id: 'hosting-docker',
        title: 'Docker Deployment',
        category: 'Self Hosting',
        description: 'Run Nexora in containerized production environments with non-root security and persistent cache mounts.',
        updatedAt: '2026-08-30',
        sections: [
          {
            id: 'docker-run',
            title: 'Quick Docker Run',
            content: `Nexora provides a production-hardened multi-stage Dockerfile running on Python 3.11-slim with non-root appuser (UID 1000).`,
            codeTabs: [
              {
                language: 'bash',
                label: 'Build & Run Container',
                code: `# 1. Build Docker image\ndocker build -t nexora-mcp:latest .\n\n# 2. Run container exposing port 8000\ndocker run -d \\\n  --name nexora-server \\\n  -p 8000:8000 \\\n  -e LOG_LEVEL=INFO \\\n  -e RATE_LIMIT_ENABLED=true \\\n  -v nexora_cache:/home/appuser/.youtube_research_mcp \\\n  nexora-mcp:latest`,
              },
            ],
          },
        ],
      },
      {
        id: 'hosting-env-vars',
        title: 'Environment Variables',
        category: 'Self Hosting',
        description: 'Complete reference of all configuration settings and environment variables.',
        updatedAt: '2026-08-30',
        sections: [
          {
            id: 'env-table',
            title: 'Configuration Settings',
            content: `| Variable | Default | Description |
| :--- | :--- | :--- |
| \`MCP_TRANSPORT\` | \`http\` | Transport protocol (\`http\`, \`sse\`, \`stdio\`) |
| \`MCP_PORT\` / \`PORT\` | \`8000\` | Effective listening port |
| \`CACHE_BACKEND\` | \`sqlite\` | Cache driver (\`sqlite\`, \`redis\`, \`memory\`) |
| \`RATE_LIMIT_ENABLED\`| \`true\` | Enables token-bucket limiter |
| \`RATE_LIMIT_RPS\` | \`10.0\` | Sustained requests per second |
| \`RATE_LIMIT_BURST\` | \`20\` | Maximum burst tokens |
| \`ADMIN_API_KEY\` | \`None\` | Secret key for administrative endpoints |`,
          },
        ],
      },
      {
        id: 'hosting-railway',
        title: 'Railway Cloud Deployment',
        category: 'Self Hosting',
        description: 'Deploy Nexora directly on Railway with dynamic port mapping, health checks, and zero downtime.',
        updatedAt: '2026-08-30',
        sections: [
          {
            id: 'railway-json',
            title: 'Railway Configuration',
            content: `Nexora includes native railway.json configured for containerized deployment:

\`\`\`json
{
  "$schema": "https://railway.com/railway.schema.json",
  "build": {
    "builder": "DOCKERFILE",
    "dockerfilePath": "Dockerfile"
  },
  "deploy": {
    "restartPolicyType": "ON_FAILURE",
    "restartPolicyMaxRetries": 10,
    "healthcheckPath": "/",
    "healthcheckTimeout": 120
  }
}
\`\`\``,
          },
        ],
      },
    ],
  },
  {
    id: 'architecture',
    title: 'Architecture',
    icon: 'Cpu',
    pages: [
      {
        id: 'arch-retrieval-pipeline',
        title: 'Retrieval Pipeline',
        category: 'Architecture',
        description: 'Deep dive into the multi-stage video intelligence, InnerTube rotation, and transcript extraction pipeline.',
        updatedAt: '2026-08-30',
        sections: [
          {
            id: 'pipeline-flow',
            title: 'Multi-Tier Provider Routing',
            content: `Nexora implements a resilient multi-tier retrieval pipeline:
1. **Tier 1 (Direct InnerTube)**: Shared HTTP/2 connection pool with anti-bot Android/Web/TV client context rotation.
2. **Tier 2 (yt-dlp Subprocess)**: Automatic subprocess fallback with process timeouts for age-gated or complex caption formats.
3. **Tier 3 (Commercial Failover)**: Extensible API connector hooks (Supadata/SearchApi) for 99.99% critical enterprise uptime.`,
          },
        ],
      },
      {
        id: 'arch-hybrid-rrf',
        title: 'Hybrid RRF & Semantic Search',
        category: 'Architecture',
        description: 'How Nexora fuses BM25s sparse lexical scoring with FastEmbed dense vectors for sub-second pinpointing.',
        updatedAt: '2026-08-30',
        sections: [
          {
            id: 'rrf-math',
            title: 'Reciprocal Rank Fusion Algorithm',
            content: `Nexora combines lexical and dense semantic rankings using Reciprocal Rank Fusion:
$$RRF\\_Score(d) = \\frac{1}{60 + r_{BM25}(d)} + \\frac{1}{60 + r_{Vector}(d)}$$
This guarantees that exact matches (e.g. error codes, version numbers) and semantic paraphrases (e.g. conceptual explanations) both score high confidence.`,
          },
        ],
      },
      {
        id: 'arch-caching-concurrency',
        title: 'Caching & Concurrency',
        category: 'Architecture',
        description: 'SingleFlight request coalescing, SQLite WAL mode, and capability-level circuit breakers.',
        updatedAt: '2026-08-30',
        sections: [
          {
            id: 'singleflight-details',
            title: 'SingleFlight Mutex Locking',
            content: `Prevents upstream cache stampedes. When 50 concurrent requests hit the server for the same video transcript, exactly 1 request executes upstream while the remaining 49 await the result asynchronously on an event lock.`,
          },
        ],
      },
      {
        id: 'arch-security',
        title: 'Security Architecture',
        category: 'Architecture',
        description: 'Threat modeling, SSRF prevention, regex validation, non-root containers, and zero credential leakage.',
        updatedAt: '2026-08-30',
        sections: [
          {
            id: 'threat-model',
            title: 'Security Controls',
            content: `* **Strict Input Validation**: Strict 11-character regex validation on video IDs (\`^[a-zA-Z0-9_-]{11}$\`) prevents command injection and SSRF.
* **Non-Root Execution**: Runs inside Docker as unprivileged user \`appuser\` (UID 1000).
* **Zero Credential Leakage**: Admin API key comparisons use \`secrets.compare_digest\` for constant-time evaluation.`,
          },
        ],
      },
    ],
  },
  {
    id: 'resources',
    title: 'Resources',
    icon: 'HelpCircle',
    pages: [
      {
        id: 'faq',
        title: 'FAQ',
        category: 'Resources',
        description: 'Frequently asked questions regarding Nexora MCP, API keys, and rate limits.',
        updatedAt: '2026-08-30',
        sections: [
          {
            id: 'faq-list',
            title: 'Common Questions',
            content: `### Do I need a YouTube API key?
No. Nexora operates with zero API keys required for public search and transcript extraction.

### Does it work with Claude Desktop, Cursor, and OpenCode?
Yes! Nexora natively supports Streamable HTTP MCP (protocol 2024-11-05). Simply configure the remote URL \`https://youtube-research-mcp-production.up.railway.app/mcp\`.

### What languages are supported?
All major languages including English, Hindi (Devanagari), Spanish, Chinese (Simplified/Traditional), Japanese, Korean (Hangul), German, French, and Russian.`,
          },
        ],
      },
      {
        id: 'troubleshooting',
        title: 'Troubleshooting',
        category: 'Resources',
        description: 'Diagnose and resolve common connection errors and YouTube restrictions.',
        updatedAt: '2026-08-30',
        sections: [
          {
            id: 'troubleshooting-list',
            title: 'Resolving Issues',
            content: `1. **"No captions available for video"**: The video owner may have disabled captions. Check with another video ID.
2. **"429 Rate Limit Exceeded"**: Wait 1–2 seconds for your token bucket to refill.
3. **"Connection Refused / Timeout"**: Ensure your client is targeting \`https://youtube-research-mcp-production.up.railway.app/mcp\` over HTTPS.`,
          },
        ],
      },
      {
        id: 'changelog',
        title: 'Changelog',
        category: 'Resources',
        description: 'Version history and release notes for the Nexora platform.',
        updatedAt: '2026-08-30',
        sections: [
          {
            id: 'v2-0-0',
            title: 'v2.0.0 — Master Brand Migration & Streamable HTTP',
            content: `* Transitioned to **Nexora** master brand and **Nexora MCP** positioning.
* Added live Streamable HTTP deployment on Railway.
* Implemented in-process Hybrid RRF search (\`youtube_find_in_video\`).
* Added SingleFlight request coalescing and capability circuit breakers.
* 122/122 backend tests passing.`,
          },
        ],
      },
    ],
  },
];
