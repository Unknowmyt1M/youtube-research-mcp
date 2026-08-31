# Transcript Acquisition & Cost-Protection Invariants

## 1. Multi-Tier Routing Architecture
Always structure acquisition into 4 isolated tiers:
- **Tier 0**: Fast In-Process / Redis Cache (with SingleFlight request deduplication).
- **Tier 1**: Direct Open-Source Free Providers (`YouTubeTranscriptApi`, `yt-dlp`, `InnerTube`).
- **Tier 2**: Proxied Free Providers / Residential Route (only invoked if Tier 1 hits datacenter/IP challenges).
- **Tier 2.5 (Cost Guard)**: Fast-fail if any free provider confirms verified content absence (`NoTranscriptFound`, `TranscriptsDisabled`, `VideoUnavailable`, `InvalidVideoId`).
- **Tier 3**: Commercial Fallback (`Supadata`) — STRICT LAST RESORT ONLY.

## 2. Isolation Invariants
- **Never Promote Paid Providers**: Commercial providers must NEVER participate in adaptive sorting with free providers or be promoted to Tier 1/2 regardless of historical success rates.
- **Daily Budget Caps**: Always check and enforce daily quota limits (`SUPADATA_MAX_DAILY_REQUESTS`) before invoking commercial providers.
- **Provider Provenance**: Every returned result model MUST include explicit `provider` provenance metadata.
- **Safe Negative Caching**: Only cache negative results for verified content absences with short TTLs (10 min); never poison cache with transient network/IP errors.
