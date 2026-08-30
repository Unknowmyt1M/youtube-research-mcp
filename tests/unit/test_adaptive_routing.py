import pytest
from unittest.mock import AsyncMock, patch

from youtube_research_mcp.providers.base import (
    CircuitState,
    ProviderCapability,
)
from youtube_research_mcp.services.router import ProviderRouter


def test_adaptive_provider_sorting_prefers_healthy_fast_providers():
    """Verify adaptive routing sorts providers by circuit state, success rate, and latency."""
    router = ProviderRouter()

    # InnerTube: CLOSED, 100% success, 25ms avg latency
    router.innertube.health.record_success(ProviderCapability.SEARCH, 25.0)
    router.innertube.health.record_success(ProviderCapability.SEARCH, 25.0)

    # YtDlp: CLOSED, 50% success (1 success, 1 failure), 300ms avg latency
    router.ytdlp.health.record_success(ProviderCapability.SEARCH, 300.0)
    router.ytdlp.health.record_failure(ProviderCapability.SEARCH, "Slow")

    candidates = router._get_adaptive_providers(
        router.search_providers, ProviderCapability.SEARCH
    )

    assert len(candidates) == 2
    assert candidates[0].name == "InnerTube"
    assert candidates[1].name == "yt-dlp"


def test_adaptive_provider_sorting_bypasses_open_circuits():
    """Verify providers with OPEN circuits are excluded from executable candidates."""
    router = ProviderRouter()

    # Trip InnerTube search circuit
    for _ in range(5):
        router.innertube.health.record_failure(ProviderCapability.SEARCH, "429 blocked")

    assert router.innertube.health.can_execute(ProviderCapability.SEARCH) is False

    candidates = router._get_adaptive_providers(
        router.search_providers, ProviderCapability.SEARCH
    )

    assert len(candidates) == 1
    assert candidates[0].name == "yt-dlp"
