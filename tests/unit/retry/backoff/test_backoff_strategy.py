import pytest
import asyncio
import random
import time
from unittest.mock import AsyncMock, MagicMock, patch
from typing import List, Optional

class AdaptiveBackoffManager:
    """Manages retry backoff with adaptive strategies and jitter."""
    
    def __init__(self, base_delay: float = 1.0, max_delay: float = 60.0):
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.success_streak = 0
        self.failure_streak = 0
        self.jitter_factor = 0.1
        self.delay_history = []
        self.error_counts = {}
        self.last_backoff = None

    def add_jitter(self, delay: float) -> float:
        """Add randomized jitter to delay."""
        jitter = delay * self.jitter_factor
        return delay + random.uniform(-jitter, jitter)

    def get_delay(self, attempt: int, error_type: Optional[str] = None) -> float:
        """Calculate delay with exponential backoff and jitter."""
        # Track error types
        if error_type:
            self.error_counts[error_type] = self.error_counts.get(error_type, 0) + 1

        # Base exponential backoff
        delay = min(self.base_delay * (2 ** attempt), self.max_delay)
        
        # Adjust based on error type
        if error_type == "rate_limit" and self.error_counts.get("rate_limit", 0) > 3:
            delay *= 1.5  # Increase delay for persistent rate limits
        elif error_type == "timeout" and self.error_counts.get("timeout", 0) > 3:
            delay *= 1.2  # Moderate increase for timeouts

        # Apply jitter
        final_delay = self.add_jitter(delay)
        self.delay_history.append(final_delay)
        self.last_backoff = final_delay
        return final_delay

    def record_result(self, success: bool):
        """Update strategy based on result."""
        if success:
            self.success_streak += 1
            self.failure_streak = 0
            if self.success_streak >= 5:
                # Increase jitter on consistent success
                self.jitter_factor = min(self.jitter_factor * 1.5, 0.5)
                self.success_streak = 0
        else:
            self.failure_streak += 1
            self.success_streak = 0
            if self.failure_streak >= 3:
                # Decrease jitter on consistent failure
                self.jitter_factor = max(self.jitter_factor * 0.5, 0.01)
                self.failure_streak = 0

@pytest.mark.asyncio
async def test_basic_backoff():
    """Test basic backoff functionality."""
    backoff = AdaptiveBackoffManager(base_delay=0.1, max_delay=1.0)
    delays = []
    
    # Test increasing delays
    for attempt in range(5):
        delay = backoff.get_delay(attempt)
        delays.append(delay)
        
    # Verify exponential increase
    assert all(delays[i] < delays[i+1] for i in range(len(delays)-1))
    assert all(delay <= backoff.max_delay for delay in delays)

@pytest.mark.asyncio
async def test_jitter_variation():
    """Test jitter adds appropriate variation."""
    backoff = AdaptiveBackoffManager(base_delay=0.1)
    base_delays = []
    jittered_delays = []
    
    # Collect multiple delays for the same attempt
    for _ in range(10):
        base = 0.1 * (2 ** 1)  # Second attempt
        jittered = backoff.get_delay(1)
        base_delays.append(base)
        jittered_delays.append(jittered)
    
    # Verify jitter adds variation
    assert len(set(jittered_delays)) > len(set(base_delays))
    assert all(abs(d - base_delays[0]) <= base_delays[0] * backoff.jitter_factor 
              for d in jittered_delays)

@pytest.mark.asyncio
async def test_error_type_adaptation():
    """Test backoff adaptation based on error types."""
    backoff = AdaptiveBackoffManager(base_delay=0.1)
    rate_limit_delays = []
    timeout_delays = []
    
    # Test rate limit errors
    for attempt in range(5):
        delay = backoff.get_delay(attempt, "rate_limit")
        rate_limit_delays.append(delay)
    
    # Reset and test timeout errors
    backoff = AdaptiveBackoffManager(base_delay=0.1)
    for attempt in range(5):
        delay = backoff.get_delay(attempt, "timeout")
        timeout_delays.append(delay)
    
    # Rate limit delays should be longer than timeout delays
    assert max(rate_limit_delays) > max(timeout_delays)

@pytest.mark.asyncio
async def test_adaptive_jitter():
    """Test jitter adaptation based on success/failure patterns."""
    backoff = AdaptiveBackoffManager(base_delay=0.1)
    initial_jitter = backoff.jitter_factor
    
    # Simulate success streak
    for _ in range(5):
        backoff.record_result(True)
    
    increased_jitter = backoff.jitter_factor
    assert increased_jitter > initial_jitter
    
    # Simulate failure streak
    for _ in range(3):
        backoff.record_result(False)
    
    final_jitter = backoff.jitter_factor
    assert final_jitter < increased_jitter

@pytest.mark.asyncio
async def test_backoff_with_real_requests(twitter_api, social_post):
    """Test backoff strategy with simulated API requests."""
    backoff = AdaptiveBackoffManager(base_delay=0.1, max_delay=1.0)
    
    # Mock session with varying responses
    mock_session = AsyncMock()
    request_count = 0
    
    async def mock_response():
        nonlocal request_count
        request_count += 1
        
        if request_count <= 3:  # First 3 rate limits
            delay = backoff.get_delay(request_count, "rate_limit")
            await asyncio.sleep(delay)
            return MagicMock(status=429, headers={"Retry-After": "1"})
        else:  # Then succeed
            return MagicMock(
                status=200,
                ok=True,
                json=AsyncMock(return_value={"data": {"id": "123"}})
            )
    
    mock_session.post.side_effect = lambda *args, **kwargs: AsyncMock(
        __aenter__=AsyncMock(return_value=mock_response())
    )()

    with patch.object(twitter_api, "session", mock_session):
        start_time = time.time()
        
        # Attempt request until success
        while True:
            try:
                result = await twitter_api.post(social_post)
                backoff.record_result(True)
                break
            except Exception:
                backoff.record_result(False)
                continue
        
        total_time = time.time() - start_time
        
        # Verify backoff behavior
        assert len(backoff.delay_history) == 3  # Three rate limits
        assert all(d > 0 for d in backoff.delay_history)  # All delays positive
        assert total_time > sum(backoff.delay_history)  # Total time includes delays

@pytest.mark.asyncio
async def test_backoff_max_delay():
    """Test backoff respects maximum delay limit."""
    backoff = AdaptiveBackoffManager(base_delay=0.1, max_delay=1.0)
    
    # Test many attempts
    delays = []
    for attempt in range(10):
        delay = backoff.get_delay(attempt)
        delays.append(delay)
    
    # Verify max delay is respected
    assert all(delay <= backoff.max_delay for delay in delays)
    assert any(delay == backoff.max_delay for delay in delays[-3:])  # Later attempts hit max

@pytest.mark.asyncio
async def test_concurrent_backoff_handling():
    """Test backoff handling with concurrent requests."""
    backoff = AdaptiveBackoffManager(base_delay=0.1, max_delay=1.0)
    results = []
    
    async def worker(worker_id: int, attempts: int):
        delays = []
        for attempt in range(attempts):
            delay = backoff.get_delay(attempt)
            delays.append(delay)
            await asyncio.sleep(delay)
        results.append((worker_id, delays))
    
    # Run concurrent workers
    tasks = [
        worker(1, 3),
        worker(2, 2),
        worker(3, 4)
    ]
    
    await asyncio.gather(*tasks)
    
    # Verify results
    assert len(results) == 3
    assert all(len(delays) == attempts 
              for worker_id, delays in results 
              for attempts in [2, 3, 4] 
              if worker_id == [2, 1, 3][attempts-2])
