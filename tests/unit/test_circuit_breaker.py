import time
import pytest

from youtube_research_mcp.providers.base import (
    CapabilityCircuitBreaker,
    CapabilityProviderHealth,
    CircuitState,
    ProviderCapability,
)


def test_circuit_breaker_state_transitions():
    cb = CapabilityCircuitBreaker(
        capability=ProviderCapability.SEARCH,
        fail_threshold=3,
        cooldown_seconds=0.1,  # Short cooldown for test
    )

    assert cb.state == CircuitState.CLOSED
    assert cb.can_execute() is True

    # 1. Record 2 failures (below threshold)
    cb.record_failure("error 1")
    cb.record_failure("error 2")
    assert cb.state == CircuitState.CLOSED
    assert cb.can_execute() is True

    # 2. Record 3rd failure (trips to OPEN)
    cb.record_failure("error 3")
    assert cb.state == CircuitState.OPEN
    assert cb.can_execute() is False

    # 3. Wait for cooldown -> transitions to HALF_OPEN on first probe
    time.sleep(0.15)
    # First probe request allowed
    assert cb.can_execute() is True
    assert cb.state == CircuitState.HALF_OPEN
    assert cb.probe_in_flight is True

    # Concurrent 2nd caller while probe is in flight -> blocked!
    assert cb.can_execute() is False

    # 4. Probe fails -> returns to OPEN
    cb.record_failure("probe failed")
    assert cb.state == CircuitState.OPEN
    assert cb.can_execute() is False

    # 5. Wait for cooldown again -> Probe succeeds -> resets to CLOSED
    time.sleep(0.15)
    assert cb.can_execute() is True
    cb.record_success(latency_ms=15.0)
    assert cb.state == CircuitState.CLOSED
    assert cb.failure_count == 0
    assert cb.can_execute() is True


def test_capability_isolation():
    health = CapabilityProviderHealth("TestProvider")

    # Trip search capability
    health.record_failure(ProviderCapability.SEARCH, "Search rate limited")
    health.record_failure(ProviderCapability.SEARCH, "Search rate limited")
    health.record_failure(ProviderCapability.SEARCH, "Search rate limited")

    assert health.can_execute(ProviderCapability.SEARCH) is False

    # Metadata and Transcript must remain healthy and independent!
    assert health.can_execute(ProviderCapability.METADATA) is True
    assert health.can_execute(ProviderCapability.TRANSCRIPT) is True
