import asyncio
import pytest
import time
from pathlib import Path
from typing import AsyncGenerator
from social_integrator.utils.rate_limiting import RateLimiter, RateLimitError, FileRateLimitStorage
from tests.utils.timing import TimingContext

pytestmark = pytest.mark.asyncio

@pytest.fixture
def tmp_storage_dir(tmp_path):
    """Create temporary directory for rate limit storage."""
    storage_dir = tmp_path / "rate_limits"
    storage_dir.mkdir()
    return storage_dir

@pytest.fixture
async def rate_limiter(tmp_storage_dir, event_loop) -> AsyncGenerator[RateLimiter, None]:
    """Create a rate limiter instance."""
    storage = FileRateLimitStorage(str(tmp_storage_dir))
    limiter = RateLimiter(calls=5, period=1.0, key="test_limiter", storage=storage)
    
    # Wait for initial state to load
    if limiter._load_task:
        try:
            await asyncio.wait_for(limiter._load_task, timeout=1.0)
        except (asyncio.TimeoutError, Exception):
            if limiter._load_task and not limiter._load_task.done():
                limiter._load_task.cancel()
                try:
                    await limiter._load_task
                except (asyncio.CancelledError, Exception):
                    pass
    
    try:
        yield limiter
    finally:
        if not limiter._closed:
            try:
                await asyncio.wait_for(limiter.close(), timeout=0.5)
            except (asyncio.TimeoutError, asyncio.CancelledError, Exception):
                pass

async def test_basic_rate_limiting(rate_limiter):
    """Test basic rate limiting functionality."""
    # Should allow 5 requests immediately
    for _ in range(5):
        await rate_limiter.acquire()
    
    # 6th request should fail
    with pytest.raises(RateLimitError) as exc_info:
        await rate_limiter.acquire()
    
    assert exc_info.value.retry_after > 0
    assert exc_info.value.retry_after <= 1.0

async def test_sliding_window(rate_limiter):
    """Test sliding window behavior."""
    async with TimingContext(timeout=2.0) as timing:
        # Make 3 requests
        for _ in range(3):
            await rate_limiter.acquire()
        
        # Wait for half the window
        await asyncio.sleep(0.5)
        timing.assert_min_elapsed(0.5)
        
        # Should allow 2 more requests
        for _ in range(2):
            await rate_limiter.acquire()
        
        # Get metrics
        metrics = await rate_limiter.get_metrics()
        assert metrics["current_usage"] == 5
        assert metrics["total_requests"] == 5
        assert metrics["total_throttled"] == 0

async def test_persistence(tmp_storage_dir):
    """Test rate limiter state persistence."""
    storage = FileRateLimitStorage(str(tmp_storage_dir))
    
    # First limiter: make requests and save state
    limiter1 = RateLimiter(calls=5, period=1.0, key="persist_test", storage=storage)
    try:
        for _ in range(3):
            await limiter1.acquire()
        await limiter1.close()
        
        # Second limiter: verify state was loaded
        limiter2 = RateLimiter(calls=5, period=1.0, key="persist_test", storage=storage)
        try:
            metrics = await limiter2.get_metrics()
            assert metrics["total_requests"] == 3
            
            # Should only allow 2 more requests
            for _ in range(2):
                await limiter2.acquire()
            
            with pytest.raises(RateLimitError):
                await limiter2.acquire()
        finally:
            await limiter2.close()
    finally:
        if not limiter1._closed:
            await limiter1.close()

async def test_wait_for_token(rate_limiter):
    """Test waiting for token availability."""
    async with TimingContext(timeout=2.0) as timing:
        # Fill up the rate limiter
        for _ in range(5):
            await rate_limiter.acquire()
        
        # Start waiting for token with timeout
        start_time = time.monotonic()
        got_token = await rate_limiter.wait_for_token(timeout=0.5)
        elapsed = time.monotonic() - start_time
        
        assert not got_token  # Should timeout
        timing.assert_min_elapsed(0.5)  # Should have waited for timeout
        
        # Wait for full period
        await asyncio.sleep(1.0)
        
        # Should get token now
        got_token = await rate_limiter.wait_for_token(timeout=0.1)
        assert got_token

async def test_concurrent_access(rate_limiter):
    """Test concurrent access to rate limiter."""
    async def make_request():
        try:
            await rate_limiter.acquire()
            return True
        except RateLimitError:
            return False
    
    # Launch 10 concurrent requests
    tasks = [make_request() for _ in range(10)]
    results = await asyncio.gather(*tasks)
    
    # Exactly 5 should succeed
    assert sum(results) == 5
    
    metrics = await rate_limiter.get_metrics()
    assert metrics["total_requests"] == 10
    assert metrics["total_throttled"] == 5
    assert metrics["max_concurrent"] == 5

async def test_cleanup_efficiency(rate_limiter):
    """Test cleanup efficiency with many requests."""
    # Make many requests just under the limit
    for _ in range(100):
        try:
            await rate_limiter.acquire()
        except RateLimitError:
            await asyncio.sleep(0.1)
    
    # Get metrics to ensure state is loaded
    metrics = await rate_limiter.get_metrics()
    
    # Check that cleanup kept the request list manageable
    assert len(rate_limiter._request_times) <= rate_limiter.calls * 2

async def test_metrics_accuracy(rate_limiter):
    """Test accuracy of metrics collection."""
    async with TimingContext(timeout=3.0) as timing:
        # Fill up the rate limiter
        for _ in range(5):  # calls=5 in fixture
            await rate_limiter.acquire()
        
        # These should all fail since we're at the limit
        for _ in range(3):
            try:
                await rate_limiter.acquire()
            except RateLimitError:
                pass
        
        metrics = await rate_limiter.get_metrics()
        assert metrics["total_requests"] == 8  # 5 successful + 3 failed
        assert metrics["total_throttled"] == 3  # 3 failed requests
        assert metrics["current_usage"] == 5    # 5 requests in current window
        assert metrics["utilization"] == 100    # At capacity
        
        # Wait for window to expire
        await asyncio.sleep(1.1)
        timing.assert_min_elapsed(1.1)
        
        # Verify window has cleared
        metrics = await rate_limiter.get_metrics()
        assert metrics["current_usage"] == 0
        
        # Make new requests
        for _ in range(3):
            await rate_limiter.acquire()
        
        # Final metrics check
        metrics = await rate_limiter.get_metrics()
        assert metrics["total_requests"] == 11  # 8 previous + 3 new
        assert metrics["total_throttled"] == 3  # Still 3 failed requests
        assert metrics["current_usage"] == 3    # Only new requests in window
        assert metrics["utilization"] == 60     # 3/5 * 100

async def test_rate_limiter_cleanup(rate_limiter):
    """Test that rate limiter properly cleans up resources."""
    async with TimingContext(timeout=1.0):
        # Use the rate limiter
        await rate_limiter.acquire()
        
        # Close it
        await rate_limiter.close()
        
        # Verify it's marked as closed
        assert rate_limiter._closed
        
        # Verify we can't use it after closing
        with pytest.raises(RuntimeError):
            await rate_limiter.acquire()

async def test_rate_limiter_load_state_timeout(tmp_storage_dir):
    """Test that rate limiter handles state loading timeouts."""
    storage = FileRateLimitStorage(str(tmp_storage_dir))
    
    async with TimingContext(timeout=2.0):
        # Create a rate limiter with a very short timeout
        limiter = RateLimiter(
            calls=5,
            period=1.0,
            key="timeout_test",
            storage=storage
        )
        
        try:
            # Wait for state to load
            await asyncio.wait_for(limiter._load_task, timeout=0.1)
        except asyncio.TimeoutError:
            # Should still be able to use the limiter even if state load times out
            await limiter.acquire()
        finally:
            await limiter.close()
