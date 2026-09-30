import os
from typing import List

class ProxyPoolConfig:
    """Configuration settings for dynamic public proxy pool manager."""

    # Enable / disable dynamic proxy pool
    ENABLED: bool = os.getenv("PROXY_POOL_ENABLED", "true").lower() in ("true", "1", "yes")

    # Refresh interval in seconds (default: 15 minutes)
    REFRESH_INTERVAL_SECONDS: int = int(os.getenv("PROXY_POOL_REFRESH_INTERVAL", "900"))

    # Timeout in seconds for individual proxy validation requests
    VALIDATION_TIMEOUT_SECONDS: float = float(os.getenv("PROXY_POOL_TIMEOUT", "6.0"))

    # Maximum concurrent validation workers
    MAX_VALIDATION_CONCURRENCY: int = int(os.getenv("PROXY_POOL_CONCURRENCY", "40"))

    # Maximum healthy proxies kept in active pool
    MAX_POOL_SIZE: int = int(os.getenv("PROXY_POOL_MAX_SIZE", "50"))

    # Failures threshold before a proxy is evicted from memory
    MAX_CONSECUTIVE_FAILURES: int = int(os.getenv("PROXY_POOL_MAX_FAILURES", "2"))

    # Primary YouTube test endpoints for lightweight validation
    TEST_TARGET_URL: str = "https://www.youtube.com/youtubei/v1/player?prettyPrint=false"
    TEST_VIDEO_ID: str = "jNQXAC9IVRw"  # "Me at the zoo"

    # Multi-source open proxy APIs (HTTP/HTTPS/SOCKS5)
    PUBLIC_SOURCES: List[str] = [
        # ProxyScrape free API (HTTP & SOCKS5)
        "https://api.proxyscrape.com/v2/?request=displayproxies&protocol=http&timeout=5000&country=all&ssl=all&anonymity=all",
        "https://api.proxyscrape.com/v2/?request=displayproxies&protocol=socks5&timeout=5000&country=all",
        # Monosans GitHub raw lists (High reputation, hourly updated)
        "https://raw.githubusercontent.com/monosans/proxy-list/main/proxies/http.txt",
        "https://raw.githubusercontent.com/monosans/proxy-list/main/proxies/socks5.txt",
        # TheSpeedX list
        "https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/http.txt",
        "https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/socks5.txt",
        # RoosterKid raw list
        "https://raw.githubusercontent.com/roosterkid/openproxylist/main/HTTPS_RAW.txt",
        # Proxifly list
        "https://raw.githubusercontent.com/proxifly/free-proxy-list/main/proxies/all/data.txt",
    ]

    # Disk cache path for zero-delay cold restart
    @property
    def CACHE_FILE_PATH(self) -> str:
        from pathlib import Path
        cache_dir = Path.home() / ".youtube_research_mcp"
        try:
            cache_dir.mkdir(parents=True, exist_ok=True)
            return str(cache_dir / "proxy_pool.json")
        except Exception:
            return os.path.join(os.path.dirname(os.path.abspath(__file__)), "proxy_pool.json")



config = ProxyPoolConfig()
