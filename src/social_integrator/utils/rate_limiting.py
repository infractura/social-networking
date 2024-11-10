import asyncio
import time
import functools
import json
import os
from abc import ABC, abstractmethod
from typing import Optional, Any, Callable, TypeVar, ParamSpec, List, Dict, Generic, AsyncIterator, Protocol
from ..core.platform import RateLimitError

P = ParamSpec('P')
T = TypeVar('T')
ItemT = TypeVar('ItemT')
ResultT = TypeVar('ResultT')

class RateLimitStorage(Protocol):
    """Protocol for rate limit persistence."""
    
    async def save_state(self, key: str, state: Dict[str, Any]) -> None:
        """Save rate limiter state."""
        ...
    
    async def load_state(self, key: str) -> Optional[Dict[str, Any]]:
        """Load rate limiter state."""
        ...

class FileRateLimitStorage:
    """File-based rate limit storage."""
    
    def __init__(self, directory: str = ".rate_limits"):
        self.directory = directory
        os.makedirs(directory, exist_ok=True)
    
    def _get_path(self, key: str) -> str:
        return os.path.join(self.directory, f"{key}.json")
    
    async def save_state(self, key: str, state: Dict[str, Any]) -> None:
        """Save rate limiter state to file."""
        path = self._get_path(key)
        async with asyncio.Lock():
            with open(path, 'w') as f:
                json.dump(state, f)
    
    async def load_state(self, key: str) -> Optional[Dict[str, Any]]:
        """Load rate limiter state from file."""
        path = self._get_path(key)
        try:
            async with asyncio.Lock():
                with open(path) as f:
                    return json.load(f)
        except FileNotFoundError:
            return None

class RateLimiter:
    """Token bucket rate limiter."""
    
    def __init__(
        self,
        calls: int,
        period: float,
        key: Optional[str] = None,
        storage: Optional[RateLimitStorage] = None
    ):
        """Initialize rate limiter.
        
        Args:
            calls: Number of calls allowed per period
            period: Time period in seconds
            key: Unique identifier for this rate limiter
            storage: Storage backend for persistence
        """
        if calls <= 0:
            raise ValueError("calls must be positive")
        if period <= 0:
            raise ValueError("period must be positive")
            
        self.calls = calls
        self.period = period
        self.key = key or f"rate_limiter_{id(self)}"
        self.storage = storage
        
        self._request_times: List[float] = []
        self._lock = asyncio.Lock()
        
        # Metrics
        self._total_requests = 0
        self._total_throttled = 0
        self._last_reset = time.monotonic()
        self._max_concurrent = 0
        self._closed = False
        
        # Initialize state loading
        self._load_task = asyncio.create_task(self._load_state()) if storage else None

    async def _load_state(self) -> None:
        """Load persisted state if available."""
        if not self.storage:
            return
            
        state = await self.storage.load_state(self.key)
        if state:
            async with self._lock:
                now = time.monotonic()
                # Only load requests still within window
                self._request_times = [
                    t for t in state.get('request_times', [])
                    if t > (now - self.period)
                ]
                self._total_requests = state.get('total_requests', 0)
                self._total_throttled = state.get('total_throttled', 0)
                self._max_concurrent = state.get('max_concurrent', 0)
                self._last_reset = state.get('last_reset', now)

    async def _save_state(self) -> None:
        """Save current state."""
        if not self.storage:
            return
            
        state = {
            'request_times': self._request_times,
            'total_requests': self._total_requests,
            'total_throttled': self._total_throttled,
            'max_concurrent': self._max_concurrent,
            'last_reset': self._last_reset
        }
        await self.storage.save_state(self.key, state)
    
    def _cleanup_old_requests(self, now: float) -> None:
        """Remove requests outside the current window using sliding window."""
        if not self._request_times:
            return
            
        window_start = now - self.period
        
        # Binary search for the first valid request
        left, right = 0, len(self._request_times)
        while left < right:
            mid = (left + right) // 2
            if self._request_times[mid] <= window_start:
                left = mid + 1
            else:
                right = mid
        
        if left > 0:
            self._request_times = self._request_times[left:]
    
    @property
    def retry_after(self) -> float:
        """Get time until next token is available."""
        if not self._request_times:
            return 0
        
        now = time.monotonic()
        self._cleanup_old_requests(now)
        
        if len(self._request_times) < self.calls:
            return 0
        
        # Use sliding window to calculate exact wait time
        window_start = now - self.period
        oldest_request = self._request_times[0]
        
        # Calculate the exact time when a slot will be available
        time_until_slot = oldest_request - window_start
        
        # Add small buffer to prevent race conditions
        return max(0.001, time_until_slot)
    
    def get_current_capacity(self) -> int:
        """Get number of available tokens."""
        now = time.monotonic()
        self._cleanup_old_requests(now)
        return max(0, self.calls - len(self._request_times))
    
    async def wait_for_token(self, timeout: Optional[float] = None) -> bool:
        """Wait for a token to become available.
        
        Args:
            timeout: Maximum time to wait in seconds
            
        Returns:
            True if token was acquired, False if timeout occurred
            
        Raises:
            RuntimeError: If rate limiter is closed
            asyncio.TimeoutError: If timeout is reached
        """
        if self._closed:
            raise RuntimeError("Rate limiter is closed")
            
        start_time = time.monotonic()
        
        while True:
            try:
                await self.acquire()
                return True
            except RateLimitError as e:
                if timeout is not None:
                    remaining = timeout - (time.monotonic() - start_time)
                    if remaining <= 0:
                        return False
                    wait_time = min(e.retry_after, remaining)
                else:
                    wait_time = e.retry_after
                    
                await asyncio.sleep(wait_time)
            except RuntimeError:
                # Re-raise if limiter was closed while waiting
                raise
    
    async def acquire(self) -> None:
        """Acquire a token, waiting if necessary.
        
        Raises:
            RuntimeError: If rate limiter is closed
            RateLimitError: If rate limit is exceeded
        """
        if self._closed:
            raise RuntimeError("Rate limiter is closed")
            
        # Ensure state is loaded before first use if storage is used
        if self._load_task is not None:
            await self._load_task
            self._load_task = None  # Only load once
        
        async with self._lock:
            now = time.monotonic()
            self._cleanup_old_requests(now)
            
            # Count the request before checking limits
            self._total_requests += 1
            current_requests = len(self._request_times)
            self._max_concurrent = max(self._max_concurrent, current_requests)
            
            if current_requests >= self.calls:
                self._total_throttled += 1
                # Save state on throttle if storage is used
                if self.storage:
                    await self._save_state()
                retry_after = self.retry_after
                raise RateLimitError(
                    f"Rate limit exceeded. Retry after {retry_after:.2f}s",
                    retry_after=retry_after
                )
            
            self._request_times.append(now)
            
            # Periodically save state if storage is used
            if self.storage and self._total_requests % 100 == 0:
                await self._save_state()

    async def close(self) -> None:
        """Close the rate limiter and save final state."""
        if self._closed:
            return
            
        try:
            if self._load_task is not None:
                await self._load_task
            if self.storage:
                await self._save_state()
        finally:
            self._closed = True

    async def get_metrics(self) -> dict:
        """Get rate limiter metrics.
        
        Returns:
            Dict containing:
            - total_requests: Total number of requests
            - total_throttled: Number of throttled requests
            - current_usage: Current number of requests in window
            - max_concurrent: Maximum concurrent requests seen
            - window_reset: Seconds until window reset
            - utilization: Current utilization percentage
            - is_closed: Whether the rate limiter is closed
        
        Raises:
            RuntimeError: If rate limiter is closed
        """
        if self._closed:
            raise RuntimeError("Rate limiter is closed")
            
        # Ensure state is loaded if storage is used
        if self._load_task is not None:
            await self._load_task
            self._load_task = None
            
        now = time.monotonic()
        self._cleanup_old_requests(now)
        
        current = len(self._request_times)
        return {
            "total_requests": self._total_requests,
            "total_throttled": self._total_throttled,
            "current_usage": current,
            "max_concurrent": self._max_concurrent,
            "window_reset": self.retry_after,
            "utilization": (current / self.calls) * 100 if self.calls > 0 else 0,
            "is_closed": self._closed
        }

    def reset_metrics(self) -> None:
        """Reset all metrics counters."""
        self._total_requests = 0
        self._total_throttled = 0
        self._max_concurrent = 0
        self._last_reset = time.monotonic()

class AsyncBatcher(Generic[ItemT, ResultT]):
    """Batches async operations for efficient processing."""
    
    def __init__(
        self,
        batch_size: int,
        batch_timeout: float,
        process_func: Callable[[List[ItemT]], AsyncIterator[ResultT]]
    ):
        """Initialize batcher.
        
        Args:
            batch_size: Maximum items per batch
            batch_timeout: Maximum time to wait for batch
            process_func: Function to process batches
        """
        self.batch_size = batch_size
        self.batch_timeout = batch_timeout
        self.process_func = process_func
        self.current_batch: List[ItemT] = []
        self.batch_event = asyncio.Event()
        self.results: Dict[int, ResultT] = {}
        self.next_item_id = 0
        self._lock = asyncio.Lock()
        self._closed = False
        self._processor_task: Optional[asyncio.Task] = None
        self._pending_batches: List[List[ItemT]] = []
        self._item_futures: Dict[int, asyncio.Future] = {}
    
    async def add_item(self, item: ItemT) -> ResultT:
        """Add item to batch and wait for result.
        
        Args:
            item: Item to process
            
        Returns:
            Processing result
            
        Raises:
            RuntimeError: If batcher is closed
        """
        if self._closed:
            raise RuntimeError("Batcher is closed")
        
        async with self._lock:
            item_id = self.next_item_id
            self.next_item_id += 1
            self.current_batch.append(item)
            
            # Create future for this item
            self._item_futures[item_id] = asyncio.Future()
            
            # Start processor if needed
            if not self._processor_task or self._processor_task.done():
                self._processor_task = asyncio.create_task(
                    self._process_batches(),
                    name=f"AsyncBatcher_{id(self)}"
                )
            
            # Signal if batch is full
            if len(self.current_batch) >= self.batch_size:
                self._pending_batches.append(self.current_batch)
                self.current_batch = []
                self.batch_event.set()
        
        try:
            # Wait for result
            result = await self._item_futures[item_id]
            if isinstance(result, Exception):
                raise result
            return result
        finally:
            # Cleanup
            self._item_futures.pop(item_id, None)
    
    async def _process_batches(self) -> None:
        """Process batches of items."""
        while not self._closed or self.current_batch or self._pending_batches:
            try:
                # Check current batch
                async with self._lock:
                    if self.current_batch:
                        self._pending_batches.append(self.current_batch)
                        self.current_batch = []
                
                # Wait for batch to fill or timeout
                if not self._pending_batches:
                    try:
                        await asyncio.wait_for(
                            self.batch_event.wait(),
                            timeout=self.batch_timeout
                        )
                    except asyncio.TimeoutError:
                        continue
                    finally:
                        self.batch_event.clear()
                
                # Process pending batches
                while self._pending_batches:
                    batch = self._pending_batches.pop(0)
                    if not batch:
                        continue
                    
                    try:
                        item_id = self.next_item_id - len(batch)
                        async for result in self.process_func(batch):
                            if item_id in self._item_futures:
                                self._item_futures[item_id].set_result(result)
                            item_id += 1
                    except Exception as e:
                        # On error, fail all remaining items
                        while item_id < self.next_item_id:
                            if item_id in self._item_futures:
                                self._item_futures[item_id].set_exception(e)
                            item_id += 1
            except Exception as e:
                # Handle unexpected errors
                for future in self._item_futures.values():
                    if not future.done():
                        future.set_exception(e)
    
    async def close(self) -> None:
        """Close batcher and process remaining items."""
        if self._closed:
            return
            
        self._closed = True
        self.batch_event.set()
        
        if self._processor_task:
            try:
                await asyncio.wait_for(self._processor_task, timeout=self.batch_timeout)
            except asyncio.TimeoutError:
                self._processor_task.cancel()
                try:
                    await self._processor_task
                except asyncio.CancelledError:
                    pass
            
            # Fail any remaining items
            for future in self._item_futures.values():
                if not future.done():
                    future.set_exception(RuntimeError("Batcher closed"))

def with_rate_limiting(calls: int, period: float) -> Callable[[Callable[P, T]], Callable[P, T]]:
    """Decorator to add rate limiting to a function.
    
    Args:
        calls: Number of calls allowed per period
        period: Time period in seconds
    
    Returns:
        Decorated function with rate limiting
    """
    limiter = RateLimiter(calls=calls, period=period)
    
    def decorator(func: Callable[P, T]) -> Callable[P, T]:
        @functools.wraps(func)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            await limiter.acquire()
            return await func(*args, **kwargs)
        return wrapper
    
    return decorator
