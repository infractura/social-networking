# Utils API Reference

Reference documentation for utility components.

## Rate Limiting

### RateLimiter

```python
class RateLimiter:
    """Rate limiter implementation using token bucket algorithm."""

    def __init__(
        self,
        calls: int,
        period: float,
        retry_after: Optional[float] = None
    ):
        """Initialize rate limiter.

        Args:
            calls: Number of calls allowed in the period
            period: Time period in seconds
            retry_after: Optional override for retry delay
        """

    async def acquire(self) -> None:
        """Acquire a token, waiting if necessary."""
```

### Rate Limiting Decorator

```python
def with_rate_limiting(
    calls_per_period: int,
    period: float,
    max_retries: int = 3
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """Decorator to apply rate limiting to a function.

    Args:
        calls_per_period: Number of calls allowed in the period
        period: Time period in seconds
        max_retries: Maximum number of retry attempts

    Returns:
        Decorated function with rate limiting
    """
```

## Batch Processing

### AsyncBatcher

```python
class AsyncBatcher:
    """Batch multiple API calls together to optimize rate limits."""

    def __init__(
        self,
        batch_size: int,
        flush_interval: float,
        rate_limiter: RateLimiter
    ):
        """Initialize batcher.

        Args:
            batch_size: Maximum items per batch
            flush_interval: Time in seconds before auto-flush
            rate_limiter: RateLimiter instance to use
        """

    async def add(self, item: Any) -> None:
        """Add item to batch, flushing if needed."""

    async def flush(self) -> None:
        """Flush current batch using rate limiter."""
```
