import pytest
import time
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Optional, Tuple, Any

class CircuitBreakerWithFallback:
    """Circuit breaker pattern implementation with fallback support."""
    
    def __init__(self, failure_threshold: int = 5, recovery_time: float = 30.0):
        self.failure_threshold = failure_threshold
        self.recovery_time = recovery_time
        self.failure_count = 0
        self.last_failure_time = None
        self.state = "closed"  # closed, open, half-open
        self.successful_probes = 0
        self.required_probes = 3

    def record_failure(self):
        """Record a failure and possibly open the circuit."""
        self.failure_count += 1
        self.last_failure_time = time.time()
        if self.failure_count >= self.failure_threshold:
            self.state = "open"
            self.successful_probes = 0

    def record_success(self):
        """Record a success and possibly close the circuit."""
        if self.state == "half-open":
            self.successful_probes += 1
            if self.successful_probes >= self.required_probes:
                self.state = "closed"
                self.failure_count = 0
                self.last_failure_time = None
        elif self.state == "closed":
            self.failure_count = max(0, self.failure_count - 1)

    def should_attempt_request(self) -> bool:
        """Check if request should be attempted based on circuit state."""
        if self.state == "closed":
            return True
        elif self.state == "open":
            if time.time() - self.last_failure_time >= self.recovery_time:
                self.state = "half-open"
                return True
            return False
        else:  # half-open
            return True

    async def execute_with_fallback(self, primary_func, fallback_func) -> Tuple[Any, str]:
        """Execute function with fallback if circuit is open."""
        if self.should_attempt_request():
            try:
                result = await primary_func()
                self.record_success()
                return result, "primary"
            except Exception as e:
                self.record_failure()
                if not self.should_attempt_request():
                    return await fallback_func(), "fallback"
                raise
        return await fallback_func(), "fallback"

@pytest.mark.asyncio
async def test_circuit_breaker_basic_operation(twitter_api, social_post):
    """Test basic circuit breaker state transitions."""
    circuit_breaker = CircuitBreakerWithFallback(failure_threshold=3, recovery_time=1.0)
    states = []
    
    # Mock responses that will fail initially
    mock_session = AsyncMock()
    request_count = 0
    
    async def primary_func():
        nonlocal request_count
        if request_count < 4:  # First 4 requests fail
            request_count += 1
            raise Exception("Service unavailable")
        return {"data": {"id": "123"}}
    
    async def fallback_func():
        return {"data": {"id": "fallback"}}

    # Record state transitions
    for _ in range(6):
        states.append(circuit_breaker.state)
        try:
            result, execution_type = await circuit_breaker.execute_with_fallback(
                primary_func, fallback_func
            )
            if execution_type == "fallback":
                assert result["data"]["id"] == "fallback"
        except Exception:
            pass

    # Verify state transitions
    assert "closed" in states  # Initial state
    assert "open" in states    # After failures
    assert states.count("closed") >= 1

@pytest.mark.asyncio
async def test_circuit_breaker_recovery(twitter_api, social_post):
    """Test circuit breaker recovery after cooling period."""
    circuit_breaker = CircuitBreakerWithFallback(failure_threshold=2, recovery_time=0.1)
    
    # Mock responses that fail then succeed
    async def primary_func():
        if circuit_breaker.failure_count < 2:
            raise Exception("Service unavailable")
        return {"data": {"id": "123"}}
    
    async def fallback_func():
        return {"data": {"id": "fallback"}}

    # Force circuit to open
    for _ in range(3):
        try:
            await circuit_breaker.execute_with_fallback(primary_func, fallback_func)
        except Exception:
            pass

    assert circuit_breaker.state == "open"
    
    # Wait for recovery time
    await asyncio.sleep(0.2)
    
    # Should transition to half-open and then closed
    result, execution_type = await circuit_breaker.execute_with_fallback(
        primary_func, fallback_func
    )
    
    assert circuit_breaker.state == "half-open"
    assert execution_type == "primary"
    assert result["data"]["id"] == "123"

@pytest.mark.asyncio
async def test_circuit_breaker_half_open_state(twitter_api, social_post):
    """Test circuit breaker behavior in half-open state."""
    circuit_breaker = CircuitBreakerWithFallback(
        failure_threshold=2,
        recovery_time=0.1
    )
    
    success_count = 0
    
    async def primary_func():
        nonlocal success_count
        if circuit_breaker.state == "half-open":
            success_count += 1
            return {"data": {"id": f"success_{success_count}"}}
        raise Exception("Service unavailable")
    
    async def fallback_func():
        return {"data": {"id": "fallback"}}

    # Force circuit to open
    for _ in range(3):
        try:
            await circuit_breaker.execute_with_fallback(primary_func, fallback_func)
        except Exception:
            pass

    # Wait for recovery time
    await asyncio.sleep(0.2)
    
    # Execute requests in half-open state
    results = []
    for _ in range(circuit_breaker.required_probes + 1):
        result, execution_type = await circuit_breaker.execute_with_fallback(
            primary_func, fallback_func
        )
        results.append((result, execution_type))
    
    # Verify successful transition back to closed
    assert circuit_breaker.state == "closed"
    assert success_count == circuit_breaker.required_probes
    assert all(r[1] == "primary" for r in results)

@pytest.mark.asyncio
async def test_circuit_breaker_with_real_requests(twitter_api, social_post):
    """Test circuit breaker with simulated API requests."""
    circuit_breaker = CircuitBreakerWithFallback(
        failure_threshold=3,
        recovery_time=0.1
    )
    
    # Mock session with varying responses
    mock_session = AsyncMock()
    request_count = 0
    
    async def mock_response():
        nonlocal request_count
        request_count += 1
        
        if request_count <= 3:  # First 3 requests fail
            return MagicMock(
                status=503,
                ok=False
            )
        return MagicMock(
            status=200,
            ok=True,
            json=AsyncMock(return_value={"data": {"id": "123"}})
        )
    
    mock_session.post.side_effect = lambda *args, **kwargs: AsyncMock(
        __aenter__=AsyncMock(return_value=mock_response())
    )()

    with patch.object(twitter_api, "session", mock_session):
        # Execute requests and track circuit state
        states = []
        results = []
        
        for _ in range(5):
            states.append(circuit_breaker.state)
            try:
                result, execution_type = await circuit_breaker.execute_with_fallback(
                    lambda: twitter_api.post(social_post),
                    lambda: {"data": {"id": "fallback"}}
                )
                results.append((result, execution_type))
            except Exception:
                results.append((None, "error"))
            await asyncio.sleep(0.05)

        # Verify circuit breaker behavior
        assert "closed" in states
        assert "open" in states
        assert any(r[1] == "fallback" for r in results)
        assert any(r[1] == "primary" for r in results)
