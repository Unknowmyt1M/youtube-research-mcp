import asyncio
import logging
import time
from typing import List, Optional
import httpx

from youtube_research_mcp.proxy_pool.config import config

logger = logging.getLogger(__name__)


class ProxyValidator:
    """Parallel validator that verifies proxies directly against YouTube endpoints."""

    # Lightweight InnerTube ANDROID player payload
    ANDROID_PAYLOAD = {
        "context": {
            "client": {
                "clientName": "ANDROID",
                "clientVersion": "20.10.38",
                "hl": "en",
                "gl": "US",
            }
        },
        "videoId": config.TEST_VIDEO_ID,
    }

    ANDROID_HEADERS = {
        "User-Agent": "com.google.android.youtube/20.10.38 (Linux; U; Android 14)",
        "Content-Type": "application/json",
        "X-YouTube-Client-Name": "3",
        "X-YouTube-Client-Version": "20.10.38",
    }

    @classmethod
    async def validate_proxy(
        cls,
        proxy_url: str,
        timeout: float = config.VALIDATION_TIMEOUT_SECONDS,
    ) -> Optional[float]:
        """Test a proxy against YouTube InnerTube endpoint.
        
        Returns latency in seconds if successful, or None if blocked/timed out.
        """
        start_t = time.perf_counter()
        try:
            async with httpx.AsyncClient(
                proxy=proxy_url,
                timeout=timeout,
                follow_redirects=True,
                http2=False,  # Use HTTP/1.1 for maximum public proxy compatibility
            ) as client:
                resp = await client.post(
                    config.TEST_TARGET_URL,
                    json=cls.ANDROID_PAYLOAD,
                    headers=cls.ANDROID_HEADERS,
                )
                if resp.status_code == 200:
                    data = resp.json()
                    status = data.get("playabilityStatus", {}).get("status", "")
                    # Check if YouTube returned actual playable response (not a captcha/login/block screen)
                    if status == "OK" or ("streamingData" in data and status != "LOGIN_REQUIRED"):
                        latency = time.perf_counter() - start_t
                        return round(latency, 3)
        except Exception:
            pass
        return None

    @classmethod
    async def validate_pool(
        cls,
        proxy_candidates: List[str],
        concurrency: int = config.MAX_VALIDATION_CONCURRENCY,
    ) -> List[dict]:
        """Validate a list of candidate proxies in parallel with bounded concurrency.
        
        Returns a list of dicts: [{'proxy': url, 'latency': float, 'last_checked': float}, ...]
        sorted by lowest latency first.
        """
        semaphore = asyncio.Semaphore(concurrency)
        valid_proxies: List[dict] = []

        async def _worker(proxy: str):
            async with semaphore:
                lat = await cls.validate_proxy(proxy)
                if lat is not None:
                    valid_proxies.append({
                        "proxy": proxy,
                        "latency": lat,
                        "consecutive_failures": 0,
                        "last_checked": time.time(),
                    })

        tasks = [_worker(p) for p in proxy_candidates]
        await asyncio.gather(*tasks, return_exceptions=True)

        # Sort by best latency
        valid_proxies.sort(key=lambda x: x["latency"])
        logger.info(f"Validation finished: {len(valid_proxies)} / {len(proxy_candidates)} proxies verified working on YouTube.")
        return valid_proxies[: config.MAX_POOL_SIZE]
