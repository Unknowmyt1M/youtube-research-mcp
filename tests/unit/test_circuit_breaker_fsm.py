import time
import pytest

from youtube_research_mcp.providers.base import (
    CapabilityCircuitBreaker,
    CapabilityProviderHealth,
    CircuitState,
    ProviderCapability,
)


def test_circuit_breaker_full_lifecycle_fsm():
    """Verify CLOSED -> failures -> OPEN -> cooldown -> HALF_OPEN -> success -> CLOSED."""
    cb = CapabilityCircuitBreaker(
        capability=ProviderCapability.TRANSCRIPT,
        fail_threshold=3,
        cooldown_seconds=0.1,
    )

    assert cb.state == CircuitState.CLOSED
    assert cb.can_execute() is True

    # 1. First two failures (below threshold)
    cb.record_failure("429 rate limited")
    assert cb.state == CircuitState.CLOSED
    assert cb.can_execute() is True

    cb.record_failure("429 rate limited")
    assert cb.state == CircuitState.CLOSED
    assert cb.can_execute() is True

    # 2. Third failure trips circuit to OPEN
    cb.record_failure("429 rate limited")
    assert cb.state == CircuitState.OPEN
    assert cb.can_execute() is False

    # 3. Before cooldown expires
    assert cb.can_execute() is False

    # 4. Wait for cooldown to expire
    time.sleep(0.12)
    # can_execute transitions to HALF_OPEN and allows 1 probe
    assert cb.can_execute() is True
    assert cb.state == CircuitState.HALF_OPEN

    # 5. Successful probe transitions back to CLOSED
    cb.record_success(latency_ms=45.0)
    assert cb.state == CircuitState.CLOSED
    assert cb.failure_count == 0
    assert cb.can_execute() is True


def test_circuit_breaker_failed_half_open_probe():
    """Verify failed probe in HALF_OPEN trips immediately back to OPEN."""
    cb = CapabilityCircuitBreaker(
        capability=ProviderCapability.SEARCH,
        fail_threshold=2,
        cooldown_seconds=0.05,
    )

    cb.record_failure("Err 1")
    cb.record_failure("Err 2")
    assert cb.state == CircuitState.OPEN

    time.sleep(0.06)
    assert cb.can_execute() is True
    assert cb.state == CircuitState.HALF_OPEN

    # Failed probe
    cb.record_failure("Probe failed")
    assert cb.state == CircuitState.OPEN
    assert cb.can_execute() is False


def test_circuit_breaker_half_open_concurrent_probe_lock():
    """Verify HALF_OPEN permits exactly ONE probe in-flight and rejects concurrent attempts."""
    cb = CapabilityCircuitBreaker(
        capability=ProviderCapability.METADATA,
        fail_threshold=1,
        cooldown_seconds=0.05,
    )

    cb.record_failure("Trip")
    assert cb.state == CircuitState.OPEN

    time.sleep(0.06)
    # First caller gets True (probe granted)
    assert cb.can_execute() is True
    assert cb.state == CircuitState.HALF_OPEN

    # Second concurrent caller gets False (probe already in-flight)
    assert cb.can_execute() is False

    # Once probe records success, circuit closes
    cb.record_success(latency_ms=10.0)
    assert cb.state == CircuitState.CLOSED
    assert cb.can_execute() is True


def test_capability_provider_health_isolation():
    """Verify failure in one capability does NOT trip other capabilities."""
    health = CapabilityProviderHealth("TestProvider")

    # Fail transcript 5 times
    for _ in range(5):
        health.record_failure(ProviderCapability.TRANSCRIPT, "Transcript error")

    # Transcript is OPEN
    assert health.can_execute(ProviderCapability.TRANSCRIPT) is False

    # Search and Metadata MUST remain CLOSED and healthy
    assert health.can_execute(ProviderCapability.SEARCH) is True
    assert health.can_execute(ProviderCapability.METADATA) is True
    assert health.breakers[ProviderCapability.SEARCH].state == CircuitState.CLOSED
    assert health.breakers[ProviderCapability.METADATA].state == CircuitState.CLOSED
