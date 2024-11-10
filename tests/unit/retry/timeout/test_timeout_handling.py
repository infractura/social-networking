import pytest
import asyncio
import time
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Dict, Optional

class AdaptiveTimeoutManager:
    """Manages timeouts with adaptive strategies."""
    
    def __init__(self, initial_timeout: float = 1.0, 
                 min_timeout: float = 0.5, 
                 max_timeout: float = 5.0):
        self.current_timeout = initial_timeout
        self.min_timeout = min_timeout
        self.max_timeout = max_timeout
        self.success_streak = 0
        self.failure_streak = 0
        self.timeout_history = []
        self.response_times = []

    def record_result(self, success: bool, response_time: Optional[float] = None):
        """Record request result and adjust timeout."""
        if success:
            self.success_streak += 1
            self.failure_streak = 0
            if response_time:
                self.response_times.append(response_time)
                # Adjust timeout based on response time patterns
                if len(self.response_times) >= 3:
                    avg_time = sum(self.response_times[-3:]) / 3
                    self.current_timeout = min(
                        self.max_timeout,
                        max(self.min_timeout, avg_time * 2)
                    )
        else:
            self.failure_streak += 1
            self.success_streak = 0
            # Increase timeout after failures
            if self.failure_streak >= 2:
                self.current_timeout = min(
                    self.max_timeout,
                    self.current_timeout * 1.5
                )

        self.timeout_history.append(self.current_timeout)

    async def execute_with_timeout(self, func, *args, **kwargs):
        """Execute function with current timeout."""
        start_time = time.time()
        try:
            async with asyncio.timeout(self.current_timeout):
                result = await func(*args, **kwargs)
            response_time = time.time() - start_time
            self.record_result(True, response_time)
            return result
        except asyncio.TimeoutError:
            self.record_result(False)
            raise

@pytest.mark.asyncio
async def test_basic_timeout_handling():
    """Test basic timeout handling functionality."""
    timeout_manager = AdaptiveTimeoutManager(initial_timeout=1.0)
    
    async def mock_request(delay: float):
        await asyncio.sleep(delay)
        return {"success": True}
    
    # Test successful request within timeout
    result = await timeout_manager.execute_with_timeout(mock_request, 0.5)
    assert result["success"]
    assert timeout_manager.success_streak == 1
    
    # Test request that times out
    with pytest.raises(asyncio.TimeoutError):
        await timeout_manager.execute_with_timeout(mock_request, 1.5)
    assert timeout_manager.failure_streak == 1

@pytest.mark.asyncio
async def test_timeout_adaptation():
    """Test timeout adaptation based on response patterns."""
    timeout_manager = AdaptiveTimeoutManager(
        initial_timeout=1.0,
        min_timeout=0.5,
        max_timeout=3.0
    )
    
    # Simulate sequence of responses
    scenarios = [
        (0.3, True),   # Fast success
        (0.4, True),   # Fast success
        (0.5, True),   # Fast success
        (1.2, False),  # Timeout
        (1.2, False),  # Timeout
        (0.6, True),   # Success with higher latency
    ]
    
    for delay, should_succeed in scenarios:
        try:
            await timeout_manager.execute_with_timeout(
                asyncio.sleep, delay
            )
        except asyncio.TimeoutError:
            assert not should_succeed
            continue
        assert should_succeed
    
    # Verify timeout adaptation
    assert len(timeout_manager.timeout_history) == len(scenarios)
    assert min(timeout_manager.timeout_history) >= timeout_manager.min_timeout
    assert max(timeout_manager.timeout_history) <= timeout_manager.max_timeout

@pytest.mark.asyncio
async def test_timeout_with_real_requests(twitter_api, social_post):
    """Test timeout handling with simulated API requests."""
    timeout_manager = AdaptiveTimeoutManager(initial_timeout=1.0)
    
    # Mock session with varying response times
    mock_session = AsyncMock()
    request_count = 0
    
    async def mock_response():
        nonlocal request_count
        request_count += 1
        
        if request_count <= 2:  # First 2 requests are fast
            await asyncio.sleep(0.3)
            return MagicMock(
                status=200,
                ok=True,
                json=AsyncMock(return_value={"data": {"id": "fast"}})
            )
        elif request_count <= 4:  # Next 2 are slow
            await asyncio.sleep(1.5)  # Should timeout
            return MagicMock()
        else:  # Rest are medium
            await asyncio.sleep(0.7)
            return MagicMock(
                status=200,
                ok=True,
                json=AsyncMock(return_value={"data": {"id": "medium"}})
            )
    
    mock_session.post.side_effect = lambda *args, **kwargs: AsyncMock(
        __aenter__=AsyncMock(return_value=mock_response())
    )()

    with patch.object(twitter_api, "session", mock_session):
        results = []
        timeouts = []
        
        for _ in range(6):
            try:
                result = await timeout_manager.execute_with_timeout(
                    twitter_api.post, social_post
                )
                results.append(result)
            except asyncio.TimeoutError:
                timeouts.append(timeout_manager.current_timeout)
        
        # Verify results
        assert len(results) == 3  # 3 successful requests
        assert len(timeouts) == 2  # 2 timeouts
        assert timeout_manager.current_timeout > 1.0  # Should have increased

@pytest.mark.asyncio
async def test_timeout_recovery():
    """Test timeout recovery after failures."""
    timeout_manager = AdaptiveTimeoutManager(
        initial_timeout=1.0,
        min_timeout=0.5,
        max_timeout=3.0
    )
    
    async def mock_request(delay: float):
        await asyncio.sleep(delay)
        return {"success": True}
    
    # Force timeout increases
    for delay in [1.2, 1.3, 1.4]:  # Sequence of failures
        try:
            await timeout_manager.execute_with_timeout(mock_request, delay)
        except asyncio.TimeoutError:
            pass
    
    high_timeout = timeout_manager.current_timeout
    
    # Recovery with faster responses
    for delay in [0.3, 0.3, 0.3]:  # Sequence of quick successes
        await timeout_manager.execute_with_timeout(mock_request, delay)
    
    # Verify timeout decreased
    assert timeout_manager.current_timeout < high_timeout

@pytest.mark.asyncio
async def test_timeout_with_concurrent_requests():
    """Test timeout handling with concurrent requests."""
    timeout_manager = AdaptiveTimeoutManager(initial_timeout=1.0)
    results = []
    
    async def worker(delay: float):
        try:
            result = await timeout_manager.execute_with_timeout(
                asyncio.sleep, delay
            )
            results.append(("success", delay))
        except asyncio.TimeoutError:
            results.append(("timeout", delay))
    
    # Run concurrent requests with different delays
    tasks = [
        worker(0.5),  # Should succeed
        worker(1.2),  # Should timeout
        worker(0.7),  # Should succeed
        worker(1.5)   # Should timeout
    ]
    
    await asyncio.gather(*tasks, return_exceptions=True)
    
    # Verify results
    successes = [r for r in results if r[0] == "success"]
    timeouts = [r for r in results if r[0] == "timeout"]
    
    assert len(successes) == 2
    assert len(timeouts) == 2
    assert all(r[1] < 1.0 for r in successes)
    assert all(r[1] > 1.0 for r in timeouts)
