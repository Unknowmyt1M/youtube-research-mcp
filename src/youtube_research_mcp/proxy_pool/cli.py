import argparse
import asyncio
import json
import logging
import sys

from youtube_research_mcp.proxy_pool.config import config
from youtube_research_mcp.proxy_pool.manager import get_proxy_pool_manager
from youtube_research_mcp.proxy_pool.validator import ProxyValidator

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")


async def main_async():
    parser = argparse.ArgumentParser(description="Nexora YouTube Proxy Pool Manager CLI")
    parser.add_argument("--status", action="store_true", help="Display active proxy pool status and metrics")
    parser.add_argument("--refresh", action="store_true", help="Manually trigger a full fetch and validation cycle")
    parser.add_argument("--test", type=str, help="Test a specific proxy URL against YouTube (e.g. http://ip:port)")
    parser.add_argument("--daemon", action="store_true", help="Run standalone proxy pool background refresher daemon")

    args = parser.parse_args()
    mgr = get_proxy_pool_manager()

    if args.test:
        print(f"Testing proxy: {args.test} against YouTube InnerTube endpoint...")
        lat = await ProxyValidator.validate_proxy(args.test)
        if lat is not None:
            print(f"✅ SUCCESS: Proxy is working! Latency: {lat}s")
        else:
            print("❌ FAILED: Proxy is blocked, unreachable, or timed out.")
        return

    if args.refresh:
        print("Triggering proxy pool refresh cycle across all public sources...")
        count = await mgr.refresh_pool()
        print(f"✅ Refresh completed. Total active YouTube proxies: {count}")
        return

    if args.daemon:
        print(f"Starting ProxyPool Daemon (sync interval: {config.REFRESH_INTERVAL_SECONDS}s)... Press Ctrl+C to stop.")
        await mgr.start_background_refresher()
        try:
            while True:
                await asyncio.sleep(1)
        except (KeyboardInterrupt, asyncio.CancelledError):
            await mgr.stop()
            print("Daemon stopped.")
        return

    # Default / --status:
    stats = mgr.get_stats()
    print("\n--- NEXORA YOUTUBE PROXY POOL STATUS ---")
    print(json.dumps(stats, indent=2))
    print("----------------------------------------\n")


def main():
    asyncio.run(main_async())


if __name__ == "__main__":
    main()
