import asyncio
import functools
import time
from typing import Optional, Callable, TypeVar, ParamSpec

P = ParamSpec('P')
T = TypeVar('T')

def retry_with_backoff(
    max_retries: int = 3,
    initial_delay: float = 0.1,
    max_delay: float = 1.0,
    backoff_factor: float = 2.0
) -> Callable[[Callable[P, T]], Callable[P, T]]:
    """Decorator for retrying flaky timing-sensitive tests with exponential backoff.
    
    Args:
        max_retries: Maximum number of retry attempts
        initial_delay: Initial delay between retries in seconds
        max_delay: Maximum delay between retries in seconds
        backoff_factor: Multiplier for delay after each retry
    """
    def decorator(func: Callable[P, T]) -> Callable[P, T]:
        @functools.wraps(func)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            delay = initial_delay
            last_exception = None
            
            for attempt in range(max_retries):
                try:
                    return await func(*args, **kwargs)
                except AssertionError as e:
                    last_exception = e
                    if attempt < max_retries - 1:
                        await asyncio.sleep(delay)
                        delay = min(delay * backoff_factor, max_delay)
            
            raise last_exception or AssertionError("Test failed after retries")
            
        return wrapper
    return decorator

class TimingContext:
    """Context manager for timing-sensitive operations.
    
    Example:
        async with TimingContext(timeout=1.0) as timing:
            await some_operation()
            timing.assert_elapsed(0.5, delta=0.1)  # Assert operation took 0.5s ± 0.1s
    """
    
    def __init__(self, timeout: float, precision: float = 0.1):
        """Initialize timing context.
        
        Args:
            timeout: Maximum allowed duration in seconds
            precision: Acceptable timing precision in seconds
        """
        self.timeout = timeout
        self.precision = precision
        self.start_time = 0.0
        self.end_time = 0.0
    
    async def __aenter__(self):
        self.start_time = time.monotonic()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        self.end_time = time.monotonic()
        if exc_type is None and self.elapsed > self.timeout:
            raise TimeoutError(
                f"Operation exceeded timeout of {self.timeout}s "
                f"(took {self.elapsed:.2f}s)"
            )
    
    @property
    def elapsed(self) -> float:
        """Get elapsed time in seconds."""
        return self.end_time - self.start_time if self.end_time else time.monotonic() - self.start_time
    
    def assert_elapsed(self, expected: float, delta: Optional[float] = None):
        """Assert that elapsed time matches expected duration.
        
        Args:
            expected: Expected duration in seconds
            delta: Acceptable deviation (defaults to context precision)
        """
        delta = delta or self.precision
        actual = self.elapsed
        assert abs(actual - expected) <= delta, \
            f"Expected duration {expected}s ± {delta}s, got {actual:.2f}s"
    
    def assert_min_elapsed(self, minimum: float):
        """Assert that at least minimum time has elapsed.
        
        Args:
            minimum: Minimum expected duration in seconds
        """
        assert self.elapsed >= minimum, \
            f"Expected minimum duration {minimum}s, got {self.elapsed:.2f}s"
    
    def assert_max_elapsed(self, maximum: float):
        """Assert that no more than maximum time has elapsed.
        
        Args:
            maximum: Maximum allowed duration in seconds
        """
        assert self.elapsed <= maximum, \
            f"Expected maximum duration {maximum}s, got {self.elapsed:.2f}s"

class TimeoutManager:
    """Manager for handling timeouts in tests.
    
    Example:
        @TimeoutManager.timeout(1.0)
        async def test_something():
            await long_running_operation()
    """
    
    @staticmethod
    def timeout(seconds: float) -> Callable[[Callable[P, T]], Callable[P, T]]:
        """Decorator to set timeout for a test function.
        
        Args:
            seconds: Timeout duration in seconds
        """
        def decorator(func: Callable[P, T]) -> Callable[P, T]:
            @functools.wraps(func)
            async def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
                async with TimingContext(timeout=seconds):
                    return await func(*args, **kwargs)
            return wrapper
        return decorator
