import pytest
import time
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

class AdaptiveRateLimiter:
    """Adaptive rate limiter for controlling request rates."""
    
    def __init__(self, initial_rate: int = 10, min_rate: int = 1, max_rate: int = 20):
        self.current_rate = initial_rate
        self.min_rate = min_rate
        self.max_rate = max_rate
        self.window_size = 60.0  # 1 minute window
        self.requests = []
        self.error_count = 0
        self.success_count = 0

    def _cleanup_old_requests(self):
        """Remove requests outside the current window."""
        current_time = time.time()
        self.requests = [t for t in self.requests if current_time - t < self.window_size]

    def record_request(self, success: bool):
        """Record request result and adjust rate."""
        current_time = time.time()
        self.requests.append(current_time)
        self._cleanup_old_requests()

        if success:
            self.success_count += 1
            if self.success_count >= 10:  # Increase rate after 10 successes
                self.current_rate = min(self.current_rate * 1.5, self.max_rate)
                self.success_count = 0
        else:
            self.error_count += 1
            if self.error_count >= 3:  # Decrease rate after 3 errors
                self.current_rate = max(self.current_rate * 0.5, self.min_rate)
                self.error_count = 0

    async def acquire(self):
        """Acquire permission to make a request."""
        self._cleanup_old_requests()
        if len(self.requests) >= self.current_rate:
            oldest_request = self.requests[0]
            wait_time = self.window_size - (time.time() - oldest_request)
            if wait_time > 0:
                await asyncio.sleep(wait_time)
            self._cleanup_old_requests()

@pytest.mark.asyncio
async def test_adaptive_rate_limiting_success(twitter_api, social_post):
    """Test rate limiting adaptation with successful requests."""
    rate_limiter = AdaptiveRateLimiter(initial_rate=5, min_rate=2, max_rate=10)
    rates = []
    
    # Mock successful responses
    mock_session = AsyncMock()
    mock_session.post.return_value.__aenter__.return_value = MagicMock(
        status=200,
        ok=True,
        json=AsyncMock(return_value={"data": {"id": "123"}})
    )

    with patch.object(twitter_api, "session", mock_session):
        # Make 15 successful requests
        for _ in range(15):
            await rate_limiter.acquire()
            rates.append(rate_limiter.current_rate)
            rate_limiter.record_request(True)
            await twitter_api.post(social_post)

    # Verify rate increased after successful requests
    assert max(rates) > rate_limiter.min_rate
    assert any(rate > 5 for rate in rates)  # Should see some rate increases

@pytest.mark.asyncio
async def test_adaptive_rate_limiting_errors(twitter_api, social_post):
    """Test rate limiting adaptation with error responses."""
    rate_limiter = AdaptiveRateLimiter(initial_rate=5, min_rate=2, max_rate=10)
    rates = []

    # Mock error responses
    mock_session = AsyncMock()
    mock_session.post.return_value.__aenter__.return_value = MagicMock(
        status=429,
        ok=False,
        headers={"Retry-After": "1"}
    )

    with patch.object(twitter_api, "session", mock_session):
        # Make requests that will fail
        for _ in range(10):
            await rate_limiter.acquire()
            rates.append(rate_limiter.current_rate)
            rate_limiter.record_request(False)
            try:
                await twitter_api.post(social_post)
            except Exception:
                pass

    # Verify rate decreased after errors
    assert min(rates) == rate_limiter.min_rate
    assert rates[-1] < rates[0]  # Final rate should be lower than initial

@pytest.mark.asyncio
async def test_adaptive_rate_limiting_mixed_pattern(twitter_api, social_post):
    """Test rate limiting adaptation with mixed success/error pattern."""
    rate_limiter = AdaptiveRateLimiter(initial_rate=5, min_rate=2, max_rate=10)
    rates = []
    success_pattern = [True, True, False, True, False, False, True, True, True, False]

    mock_session = AsyncMock()
    response_count = 0

    async def mock_response(*args, **kwargs):
        nonlocal response_count
        success = success_pattern[response_count % len(success_pattern)]
        response_count += 1
        
        if success:
            return MagicMock(
                status=200,
                ok=True,
                json=AsyncMock(return_value={"data": {"id": "123"}})
            )
        return MagicMock(status=429, headers={"Retry-After": "1"})

    mock_session.post.side_effect = lambda *args, **kwargs: AsyncMock(
        __aenter__=AsyncMock(return_value=mock_response())
    )()

    with patch.object(twitter_api, "session", mock_session):
        # Make requests following the pattern
        for success in success_pattern:
            await rate_limiter.acquire()
            rates.append(rate_limiter.current_rate)
            rate_limiter.record_request(success)
            try:
                await twitter_api.post(social_post)
            except Exception:
                pass

    # Verify rate adaptations
    assert len(rates) == len(success_pattern)
    assert min(rates) >= rate_limiter.min_rate
    assert max(rates) <= rate_limiter.max_rate
    
    # Rate should fluctuate based on success/error patterns
    rate_changes = [rates[i+1] - rates[i] for i in range(len(rates)-1)]
    assert any(change > 0 for change in rate_changes)  # Some increases
    assert any(change < 0 for change in rate_changes)  # Some decreases
