import pytest
import asyncio
from typing import List, AsyncIterator, Optional
from social_integrator.utils.rate_limiting import (
    RateLimiter,
    RateLimitError,
    with_rate_limiting,
    AsyncBatcher
)

@pytest.mark.asyncio
async def test_rate_limiter_partial_replenishment():
    """Test rate limiter with partial token replenishment."""
    limiter = RateLimiter(calls=2, period=0.2)
    
    # Use all tokens
    await limiter.acquire()
    await limiter.acquire()
    
    # Wait for partial replenishment (one token)
    await asyncio.sleep(0.15)  # Should replenish ~1.5 tokens
    
    # Should be able to acquire one token
    await limiter.acquire()
    
    # Should be rate limited again
    with pytest.raises(RateLimitError) as exc_info:
        await limiter.acquire()
    assert exc_info.value.retry_after > 0

@pytest.mark.asyncio
async def test_rate_limiter_burst_handling():
    """Test rate limiter handling of request bursts."""
    limiter = RateLimiter(calls=3, period=0.2)
    results = []
    
    async def make_request(delay: float = 0) -> bool:
        if delay:
            await asyncio.sleep(delay)
        try:
            await limiter.acquire()
            results.append(True)
            return True
        except RateLimitError:
            results.append(False)
            return False
    
    # First burst
    tasks = [
        make_request(),
        make_request(),
        make_request(),
        make_request()  # Should be rate limited
    ]
    await asyncio.gather(*tasks)
    
    # Wait for partial recovery
    await asyncio.sleep(0.15)
    
    # Second burst
    tasks = [
        make_request(),
        make_request()  # Should be rate limited
    ]
    await asyncio.gather(*tasks)
    
    assert results.count(True) == 4  # Should have 4 successful requests
    assert results.count(False) == 2  # Should have 2 rate limited requests

@pytest.mark.asyncio
async def test_async_batcher_mixed_processing(batcher_cleanup):
    """Test async batcher with mixed success/failure processing."""
    processed_items: List[str] = []
    failed_items: List[str] = []
    
    async def process_batch(items: List[str]) -> AsyncIterator[str]:
        for item in items:
            if item.endswith('_fail'):
                raise ValueError(f"Failed to process {item}")
            processed_items.append(item)
            yield f"processed_{item}"
    
    batcher = AsyncBatcher(
        batch_size=2,
        batch_timeout=0.1,
        process_func=process_batch
    )
    
    try:
        # Add mix of successful and failing items
        results = await asyncio.gather(
            batcher.add_item("item1"),
            batcher.add_item("item2_fail"),
            batcher.add_item("item3"),
            return_exceptions=True
        )
        
        assert len(processed_items) == 2  # item1 and item3
        assert any(isinstance(r, ValueError) for r in results)
    finally:
        await batcher.close()

@pytest.mark.asyncio
async def test_async_batcher_batch_size_trigger(batcher_cleanup):
    """Test async batcher batch size triggering."""
    batch_sizes: List[int] = []
    
    async def process_batch(items: List[str]) -> AsyncIterator[str]:
        batch_sizes.append(len(items))
        for item in items:
            yield f"processed_{item}"
    
    batcher = AsyncBatcher(
        batch_size=2,
        batch_timeout=1.0,  # Long timeout to ensure size triggers batch
        process_func=process_batch
    )
    
    try:
        # Add exactly batch_size items
        results = await asyncio.gather(
            batcher.add_item("item1"),
            batcher.add_item("item2")
        )
        
        assert batch_sizes == [2]  # Should process one batch of size 2
        assert all(isinstance(r, str) for r in results)
    finally:
        await batcher.close()

@pytest.mark.asyncio
async def test_rate_limiter_decorator_with_args():
    """Test rate limiting decorator with function arguments."""
    results: List[tuple] = []
    
    @with_rate_limiting(calls=2, period=0.2)
    async def test_func(arg1: str, arg2: Optional[int] = None) -> str:
        results.append((arg1, arg2))
        return f"{arg1}_{arg2 or ''}"
    
    # First two calls should work
    assert await test_func("a", 1) == "a_1"
    assert await test_func("b", 2) == "b_2"
    
    # Third call should be rate limited
    with pytest.raises(RateLimitError):
        await test_func("c", 3)
    
    assert results == [("a", 1), ("b", 2)]

@pytest.mark.asyncio
async def test_async_batcher_early_close(batcher_cleanup):
    """Test async batcher early close behavior."""
    async def process_batch(items: List[str]) -> AsyncIterator[str]:
        for item in items:
            yield f"processed_{item}"
    
    batcher = AsyncBatcher(
        batch_size=3,
        batch_timeout=1.0,
        process_func=process_batch
    )
    
    try:
        # Add one item and close immediately
        task = asyncio.create_task(batcher.add_item("item1"))
        await asyncio.sleep(0.01)  # Give time for item to be added
        await batcher.close()
        
        result = await task
        assert result == "processed_item1"
    finally:
        await batcher.close()

@pytest.mark.asyncio
async def test_rate_limiter_token_calculation():
    """Test rate limiter token calculation accuracy."""
    limiter = RateLimiter(calls=10, period=0.2)  # 50 tokens per second
    
    # Use 5 tokens
    for _ in range(5):
        await limiter.acquire()
    
    # Wait for partial replenishment
    await asyncio.sleep(0.15)  # Should replenish about 7-8 tokens
    
    # Should be able to acquire 7-8 more tokens
    acquired = 0
    for _ in range(8):
        try:
            await limiter.acquire()
            acquired += 1
        except RateLimitError:
            break
    
    assert 6 <= acquired <= 8  # Allow for timing variations

@pytest.mark.asyncio
async def test_async_batcher_concurrent_batches(batcher_cleanup):
    """Test async batcher handling multiple concurrent batches."""
    batches_processed = []
    
    async def process_batch(items: List[str]) -> AsyncIterator[str]:
        batch_id = len(batches_processed)
        batches_processed.append(items)
        for item in items:
            yield f"batch{batch_id}_{item}"
    
    batcher = AsyncBatcher(
        batch_size=2,
        batch_timeout=0.1,
        process_func=process_batch
    )
    
    try:
        # Add items that will form multiple batches
        results = await asyncio.gather(
            batcher.add_item("item1"),
            batcher.add_item("item2"),
            batcher.add_item("item3"),
            batcher.add_item("item4")
        )
        
        assert len(batches_processed) == 2  # Should have processed 2 batches
        assert all(len(batch) <= 2 for batch in batches_processed)  # Each batch should respect size limit
    finally:
        await batcher.close()
