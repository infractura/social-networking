import pytest
import asyncio
import time
from typing import Dict, Optional

class ConnectionPoolManager:
    """Manages a pool of connections with adaptive sizing."""
    
    def __init__(self, pool_size: int = 5, max_size: int = 10):
        self.pool_size = pool_size
        self.max_size = max_size
        self.active_connections = 0
        self.connection_semaphore = asyncio.Semaphore(pool_size)
        self.pool_metrics = {
            "timeouts": 0,
            "successes": 0,
            "total_time": 0.0
        }

    def adjust_pool_size(self, success: bool, response_time: float):
        """Adjust pool size based on performance metrics."""
        if success:
            self.pool_metrics["successes"] += 1
        else:
            self.pool_metrics["timeouts"] += 1

        self.pool_metrics["total_time"] += response_time
        avg_time = self.pool_metrics["total_time"] / (
            self.pool_metrics["successes"] + self.pool_metrics["timeouts"]
        )

        # Adjust pool size based on metrics
        if self.pool_metrics["timeouts"] > self.pool_metrics["successes"] / 2:
            # Too many timeouts, reduce pool size
            self.pool_size = max(1, self.pool_size - 1)
        elif avg_time < 0.2 and self.active_connections >= self.pool_size:
            # Fast responses and high utilization, increase pool size
            self.pool_size = min(self.max_size, self.pool_size + 1)

        # Update semaphore if size changed
        if self.connection_semaphore._value != self.pool_size:
            self.connection_semaphore = asyncio.Semaphore(self.pool_size)

    async def acquire(self):
        """Acquire a connection from the pool."""
        await self.connection_semaphore.acquire()
        self.active_connections += 1

    def release(self):
        """Release a connection back to the pool."""
        self.active_connections -= 1
        self.connection_semaphore.release()

@pytest.mark.asyncio
async def test_pool_basic_operation():
    """Test basic pool operations with concurrent requests."""
    pool = ConnectionPoolManager(pool_size=3, max_size=5)
    
    # Track concurrent connections
    max_concurrent = 0
    current_concurrent = 0
    
    async def make_request():
        nonlocal current_concurrent, max_concurrent
        await pool.acquire()
        try:
            current_concurrent += 1
            max_concurrent = max(max_concurrent, current_concurrent)
            await asyncio.sleep(0.01)  # Reduced from 0.1
            return {"success": True}
        finally:
            current_concurrent -= 1
            pool.release()

    # Make concurrent requests
    tasks = [make_request() for _ in range(5)]
    results = await asyncio.gather(*tasks)
    
    # Verify pool constraints were respected
    assert max_concurrent <= pool.pool_size
    assert all(isinstance(r, dict) for r in results)

@pytest.mark.asyncio
async def test_pool_size_adaptation():
    """Test pool size adaptation based on performance metrics."""
    pool = ConnectionPoolManager(pool_size=2, max_size=4)
    pool_sizes = []
    
    async def simulate_request(delay: float, success: bool):
        await pool.acquire()
        try:
            start_time = time.time()
            await asyncio.sleep(delay)
            pool.adjust_pool_size(success, time.time() - start_time)
            pool_sizes.append(pool.pool_size)
            if not success:
                raise asyncio.TimeoutError()
            return {"success": True}
        finally:
            pool.release()

    # Test scenarios with shorter delays
    scenarios = [
        (0.01, True),   # Fast success
        (0.01, True),   # Fast success
        (0.03, False),  # Slow timeout
        (0.01, True),   # Fast success
        (0.03, False),  # Slow timeout
    ]
    
    for delay, success in scenarios:
        try:
            await simulate_request(delay, success)
        except asyncio.TimeoutError:
            pass
    
    # Verify pool adaptation
    assert len(pool_sizes) == len(scenarios)
    assert min(pool_sizes) >= 1
    assert max(pool_sizes) <= pool.max_size

@pytest.mark.asyncio
async def test_pool_concurrent_load():
    """Test pool behavior under concurrent load."""
    pool = ConnectionPoolManager(pool_size=2, max_size=5)
    results = []
    
    async def worker(worker_id: int):
        for _ in range(3):  # Each worker makes 3 requests
            await pool.acquire()
            try:
                start_time = time.time()
                await asyncio.sleep(0.01)  # Reduced from 0.1
                success = worker_id % 2 == 0  # Alternate success/failure
                pool.adjust_pool_size(success, time.time() - start_time)
                results.append((worker_id, success))
            finally:
                pool.release()

    # Start multiple workers
    workers = [worker(i) for i in range(4)]
    await asyncio.gather(*workers)
    
    # Verify results
    assert len(results) == 12  # 4 workers * 3 requests
    assert pool.active_connections == 0  # All connections released
    assert pool.pool_size <= pool.max_size

@pytest.mark.asyncio
async def test_pool_error_handling():
    """Test pool behavior with error conditions."""
    pool = ConnectionPoolManager(pool_size=2, max_size=4)
    initial_active = pool.active_connections
    
    async def failing_request():
        await pool.acquire()
        try:
            raise Exception("Simulated error")
        finally:
            pool.release()

    # Test error scenarios
    for _ in range(3):
        with pytest.raises(Exception):
            await failing_request()
    
    # Verify no connection leaks
    assert pool.active_connections == initial_active
    assert pool.connection_semaphore._value == pool.pool_size

@pytest.mark.asyncio
async def test_pool_timeout_handling():
    """Test pool behavior with timeout scenarios."""
    pool = ConnectionPoolManager(pool_size=2, max_size=4)
    
    async def timeout_request(delay: float):
        await pool.acquire()
        try:
            start_time = time.time()
            try:
                async with asyncio.timeout(0.02):  # Reduced from 0.2
                    await asyncio.sleep(delay)
                success = True
            except asyncio.TimeoutError:
                success = False
            pool.adjust_pool_size(success, time.time() - start_time)
            return success
        finally:
            pool.release()

    # Test mixed timeout scenarios
    results = await asyncio.gather(
        timeout_request(0.01),  # Should succeed
        timeout_request(0.03),  # Should timeout
        timeout_request(0.01),  # Should succeed
        return_exceptions=True
    )
    
    # Verify results
    successes = [r for r in results if r is True]
    assert len(successes) == 2  # Two successes
    assert pool.active_connections == 0
    assert pool.pool_metrics["timeouts"] == 1
