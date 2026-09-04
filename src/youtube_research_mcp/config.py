from pathlib import Path
from typing import List, Literal, Optional, Union
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Global configuration for Nexora MCP (legacy: YouTube Research MCP)."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Master Branding & Metadata
    BRAND_NAME: str = "Nexora"
    PRODUCT_NAME: str = "Nexora MCP"
    TAGLINE: str = "Understand Everything. Instantly."
    DESCRIPTION: str = "AI-powered YouTube and video intelligence for AI agents."

    # Server & Transport settings (legacy identifier preserved for backwards compatibility)
    MCP_SERVER_NAME: str = "youtube-research-mcp"
    LOG_LEVEL: str = "INFO"
    MAX_CONCURRENCY: int = 10
    REQUEST_TIMEOUT: float = 25.0
    PORT: Optional[int] = None  # Dynamic cloud platform port (Railway / Render / Fly.io)
    MCP_PORT: int = 8000
    MCP_HOST: str = "0.0.0.0"
    MCP_TRANSPORT: str = "http"

    @property
    def effective_port(self) -> int:
        """Returns cloud PORT if set, otherwise MCP_PORT, defaulting to 8000."""
        if self.PORT is not None:
            return self.PORT
        return self.MCP_PORT

    # Security & Admin Authentication (SEC-001)
    ADMIN_API_KEY: Optional[str] = None  # If set, required for /api/admin/* endpoints

    # CORS Configuration (SEC-002)
    CORS_ALLOWED_ORIGINS: List[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]
    CORS_ALLOW_ALL_API: bool = True  # Allows public /api/* routes to be called from ChatGPT/external clients

    # Rate Limiting (SEC-003)
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_RPS: float = 10.0
    RATE_LIMIT_BURST: float = 20.0

    # Resource Protection Limits (RES-001, RES-002, RES-003)
    MAX_QUERY_LENGTH: int = 500
    MAX_TRANSCRIPT_SEGMENTS: int = 10000
    MAX_CACHE_ENTRIES: int = 20000

    # Cache settings
    CACHE_BACKEND: Literal["sqlite", "memory", "redis"] = "sqlite"
    CACHE_DB_PATH: str = str(Path.home() / ".youtube_research_mcp" / "cache.db")
    REDIS_URL: str = "redis://localhost:6379/0"
    REDIS_SOCKET_TIMEOUT: float = 5.0
    REDIS_CONNECT_TIMEOUT: float = 5.0
    REDIS_MAX_CONNECTIONS: int = 50
    CACHE_SCHEMA_VERSION: str = "v2"
    CACHE_TTL_SEARCH: int = 43200  # 12 hours
    CACHE_TTL_METADATA: int = 604800  # 7 days
    CACHE_TTL_TRANSCRIPT: int = 5184000  # 60 days
    NEGATIVE_CACHE_TTL: int = 600  # 10 minutes for uncaptioned/missing videos

    # Circuit Breaker settings
    CIRCUIT_BREAKER_FAIL_THRESHOLD: int = 3
    CIRCUIT_BREAKER_COOLDOWN_SECONDS: float = 30.0

    # Semantic & Retrieval settings
    USE_ONNX_EMBEDDER: bool = False
    EMBEDDING_MODEL: str = "BAAI/bge-small-en-v1.5"
    HYBRID_SEARCH_TOP_K: int = 5
    BM25_K1: float = 1.5
    BM25_B: float = 0.75
    RRF_K: int = 60
    CHUNK_TARGET_WORDS: int = 180
    CHUNK_OVERLAP_WORDS: int = 30
    MAX_RETRIEVAL_INDEXES: int = 100
    INDEX_TTL_SECONDS: int = 3600

    # Research Mode & Diversity settings
    MAX_VIDEOS_PER_CHANNEL: int = 2
    EVIDENCE_SIMILARITY_THRESHOLD: float = 0.75
    DEFAULT_FALLBACK_LANGUAGE: Optional[str] = "en"

    # Optional Commercial Keys (Isolated Fallback Tiers)
    SUPADATA_API_KEY: Optional[str] = None
    SUPADATA_API_KEY_SECONDARY: Optional[str] = None
    SUPADATA_API_KEY_TERTIARY: Optional[str] = None
    SUPADATA_MAX_DAILY_REQUESTS: Optional[int] = None
    SEARCHAPI_API_KEY: Optional[str] = None
    TRANSCRIPT_API_KEY: Optional[str] = None
    YOUTUBE_DATA_API_KEY: Optional[str] = None

    @property
    def supadata_api_keys(self) -> List[str]:
        """Returns list of unique active Supadata API keys in priority order."""
        keys = []
        for k in [self.SUPADATA_API_KEY, self.SUPADATA_API_KEY_SECONDARY, self.SUPADATA_API_KEY_TERTIARY]:
            if k and isinstance(k, str):
                cleaned = k.strip()
                if cleaned and cleaned not in keys:
                    keys.append(cleaned)
        return keys

    # HTTP & Connection Pooling / Proxy Tiers
    YOUTUBE_PROXY_ENABLED: bool = False
    RESIDENTIAL_PROXY_URL: Optional[str] = None
    HTTP_PROXY: Optional[str] = None
    HTTPS_PROXY: Optional[str] = None
    POOL_MAX_CONNECTIONS: int = 50
    POOL_MAX_KEEPALIVE: int = 20
    USER_AGENT: str = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36"
    )

    @field_validator("CORS_ALLOWED_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v


settings = Settings()
