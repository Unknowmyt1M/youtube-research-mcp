import asyncio
import httpx
from unittest.mock import AsyncMock, patch
import pytest

from youtube_research_mcp.config import settings
from youtube_research_mcp.providers.commercial import CommercialProvider
from youtube_research_mcp.providers.innertube import InnerTubeProvider
from youtube_research_mcp.utils.metrics import metrics
from youtube_research_mcp.utils.single_flight import SingleFlight


@pytest.mark.asyncio
async def test_commercial_provider_fallback_and_translation():
    """Verify CommercialProvider handles primary language failure with fallback and translate parameters."""
    provider = CommercialProvider()

    with pytest.MonkeyPatch().context() as mp:
        mp.setattr(settings, "SUPADATA_API_KEY", "mock_key")

        mock_client = AsyncMock()
        mock_client.is_closed = False

        # Primary request fails with 404, fallback request succeeds with 200
        resp_404 = AsyncMock(spec=httpx.Response)
        resp_404.status_code = 404

        resp_200 = AsyncMock(spec=httpx.Response)
        resp_200.status_code = 200
        resp_200.json.return_value = {
            "content": [
                {"offset": 0, "duration": 5.0, "text": "Hola mundo"},
                {"offset": 5000, "duration": 4.0, "text": "Bienvenidos al video"},
            ]
        }

        mock_client.get.side_effect = [resp_404, resp_200]

        with patch.object(provider, "get_client", new_callable=AsyncMock) as mock_get_client:
            mock_get_client.return_value = mock_client

            res = await provider.get_transcript(
                video_id="dQw4w9WgXcQ",
                language="es",
                fallback_language="en",
                translate_to="es",
            )

            assert res is not None
            assert res.actual_language == "es"
            assert res.fallback_used is True
            assert res.total_segments == 2
            assert len(res.segments) == 2


@pytest.mark.asyncio
async def test_single_flight_and_metrics_coalescing():
    """Verify single-flight correctly coalesces duplicate requests and increments metrics counter."""
    flight = SingleFlight()
    exec_count = 0

    async def slow_work():
        nonlocal exec_count
        exec_count += 1
        await asyncio.sleep(0.05)
        return "work_result"

    tasks = [flight.execute("key_flight_metric", slow_work) for _ in range(5)]
    results = await asyncio.gather(*tasks)

    assert exec_count == 1
    for r in results:
        assert r == "work_result"
    assert flight.coalesced_count == 4
