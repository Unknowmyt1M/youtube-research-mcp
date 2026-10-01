import asyncio
import logging
import re
from typing import List, Set
import httpx

from youtube_research_mcp.proxy_pool.config import config

logger = logging.getLogger(__name__)

# Regex pattern to extract IP:PORT or protocol://IP:PORT from raw text
PROXY_PATTERN = re.compile(
    r"(?:(?:https?|socks[45]):\/\/)?([0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}):([0-9]{2,5})"
)


class ProxyFetcher:
    """Async scraper that aggregates raw proxy endpoints across multiple public sources."""

    @staticmethod
    async def fetch_source(client: httpx.AsyncClient, url: str) -> List[str]:
        """Fetch and extract proxies from a single public endpoint."""
        results: List[str] = []
        is_socks5 = "socks5" in url.lower()
        try:
            resp = await client.get(url, timeout=12.0)
            if resp.status_code == 200:
                lines = resp.text.splitlines()
                for line in lines:
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue
                    m = PROXY_PATTERN.search(line)
                    if m:
                        ip, port = m.group(1), m.group(2)
                        import ipaddress
                        try:
                            ip_obj = ipaddress.ip_address(ip)
                            if ip_obj.is_private or ip_obj.is_loopback or ip_obj.is_reserved or ip_obj.is_link_local:
                                continue
                        except ValueError:
                            continue

                        # Normalize into standard proxy URL format
                        if line.startswith("socks5://") or is_socks5:
                            results.append(f"socks5://{ip}:{port}")
                        elif line.startswith("http://") or line.startswith("https://"):
                            results.append(f"http://{ip}:{port}")
                        else:
                            results.append(f"http://{ip}:{port}")
        except Exception as e:
            logger.debug(f"Failed to fetch proxy source '{url}': {e}")
        return results

    @classmethod
    async def fetch_all(cls) -> List[str]:
        """Fetch all public sources in parallel and return deduplicated raw proxy strings."""
        unique_proxies: Set[str] = set()
        limits = httpx.Limits(max_connections=20, max_keepalive_connections=10)

        async with httpx.AsyncClient(limits=limits, follow_redirects=True) as client:
            tasks = [cls.fetch_source(client, url) for url in config.PUBLIC_SOURCES]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            for batch in results:
                if isinstance(batch, list):
                    for proxy_str in batch:
                        unique_proxies.add(proxy_str)

        logger.info(f"Fetched {len(unique_proxies)} unique raw proxy candidates from public sources.")
        return list(unique_proxies)
