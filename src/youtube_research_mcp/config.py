from pathlib import Path
from typing import Literal, Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Global configuration for YouTube Research MCP."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Server settings
    MCP_SERVER_NAME: str = "youtube-research-mcp"
    LOG_LEVEL: str = "INFO"
    MAX_CONCURRENCY: int = 5
    REQUEST_TIMEOUT: float = 15.0

    # Cache settings
    CACHE_BACKEND: Literal["sqlite", "memory", "redis"] = "sqlite"
    CACHE_DB_PATH: str = str(Path.home() / ".youtube_research_mcp" / "cache.db")
    REDIS_URL: str = "redis://localhost:6379/0"
    CACHE_TTL_SEARCH: int = 43200  # 12 hours
    CACHE_TTL_METADATA: int = 604800  # 7 days
    CACHE_TTL_TRANSCRIPT: int = 5184000  # 60 days

    # Semantic & Retrieval settings
    USE_ONNX_EMBEDDER: bool = False
    EMBEDDING_MODEL: str = "BAAI/bge-small-en-v1.5"
    HYBRID_SEARCH_TOP_K: int = 5
    BM25_K1: float = 1.5
    BM25_B: float = 0.75
    RRF_K: int = 60
    CHUNK_TARGET_WORDS: int = 180
    CHUNK_OVERLAP_WORDS: int = 30

    # Optional Commercial Keys (Isolated Fallback Tiers)
    SUPADATA_API_KEY: Optional[str] = None
    SEARCHAPI_API_KEY: Optional[str] = None
    TRANSCRIPT_API_KEY: Optional[str] = None
    YOUTUBE_DATA_API_KEY: Optional[str] = None

    # HTTP & Proxy
    HTTP_PROXY: Optional[str] = None
    USER_AGENT: str = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36"
    )


settings = Settings()
