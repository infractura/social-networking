import pytest
import asyncio
from social_integrator.core.platform import SocialPost, PlatformError, RateLimitError
from social_integrator.utils.rate_limiting import RateLimiter
from tests.unit.core.conftest import MockPlatform

class RateLimitedPlatform(MockPlatform):
    """Mock platform with rate limiting for testing."""
    
    def __init__(self, *args, calls: int = 2, period: float = 0.2, **kwargs):
        super().__init__(*args, **kwargs)
        self.limiter = RateLimiter(calls=calls, period=period)
    
    async def post(self, post: SocialPost):
        try:
            await self.limiter.acquire()
            return await super().post(post)
        except RateLimitError as e:
            # Re-raise with retry_after
            raise RateLimitError(str(e), retry_after=self.limiter.retry_after)

@pytest.mark.asyncio
async def test_basic_rate_limiting():
    """Test basic rate limiting behavior."""
    platform = RateLimitedPlatform(auth_token="mock_token", calls=2, period=0.2)
    
    # First two calls should work
    await platform.post(SocialPost(content="Test 1"))
    await platform.post(SocialPost(content="Test 2"))
    
    # Third call should be rate limited
    with pytest.raises(RateLimitError) as exc_info:
        await platform.post(SocialPost(content="Test 3"))
    assert exc_info.value.retry_after > 0

    # After waiting full period, should work again
    await asyncio.sleep(0.3)  # Wait longer than period
    result = await platform.post(SocialPost(content="Test 4"))
    assert "id" in result

@pytest.mark.asyncio
async def test_rate_limit_recovery():
    """Test rate limit recovery over time."""
    platform = RateLimitedPlatform(auth_token="mock_token", calls=3, period=0.2)
    results = []
    
    # Use up all calls
    for i in range(3):
        result = await platform.post(SocialPost(content=f"Test {i}"))
        results.append(result)
    
    assert len(results) == 3
    
    # Should be rate limited
    with pytest.raises(RateLimitError) as exc_info:
        await platform.post(SocialPost(content="Test fail"))
    assert exc_info.value.retry_after > 0
    
    # Wait for full recovery
    await asyncio.sleep(0.3)  # Wait longer than period
    
    # Should work again
    result = await platform.post(SocialPost(content="Test recovery"))
    assert "id" in result

@pytest.mark.asyncio
async def test_concurrent_rate_limiting():
    """Test rate limiting with concurrent requests."""
    platform = RateLimitedPlatform(auth_token="mock_token", calls=2, period=0.2)
    
    # Create multiple concurrent requests
    posts = [SocialPost(content=f"Test {i}") for i in range(4)]
    
    # Gather results, some should fail with RateLimitError
    results = await asyncio.gather(
        *[platform.post(post) for post in posts],
        return_exceptions=True
    )
    
    # Should have mix of successes and rate limit errors
    successes = [r for r in results if isinstance(r, dict)]
    rate_limits = [r for r in results if isinstance(r, RateLimitError)]
    
    assert len(successes) == 2  # Should match rate limit
    assert len(rate_limits) == 2  # Remaining should be rate limited

@pytest.mark.asyncio
async def test_rate_limit_window_sliding():
    """Test rate limit window sliding behavior."""
    platform = RateLimitedPlatform(auth_token="mock_token", calls=2, period=0.2)
    
    # First call
    await platform.post(SocialPost(content="Test 1"))
    
    # Wait partial period
    await asyncio.sleep(0.1)
    
    # Second call
    await platform.post(SocialPost(content="Test 2"))
    
    # Third call should be rate limited
    with pytest.raises(RateLimitError) as exc_info:
        await platform.post(SocialPost(content="Test 3"))
    assert exc_info.value.retry_after > 0
    
    # Wait for full period
    await asyncio.sleep(0.3)  # Wait longer than period
    
    # Should work again
    result = await platform.post(SocialPost(content="Test 4"))
    assert "id" in result

@pytest.mark.asyncio
async def test_rate_limit_error_details():
    """Test rate limit error information."""
    platform = RateLimitedPlatform(auth_token="mock_token", calls=1, period=0.2)
    
    # Use up the rate limit
    await platform.post(SocialPost(content="Test 1"))
    
    # Next call should fail with detailed error
    try:
        await platform.post(SocialPost(content="Test 2"))
        pytest.fail("Should have raised RateLimitError")
    except RateLimitError as e:
        assert str(e).startswith("Rate limit exceeded")
        assert hasattr(e, "retry_after")
        assert e.retry_after > 0
