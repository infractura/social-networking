# Error Handling Guide

Learn how to handle errors effectively in Social Integrator.

## Error Types

### Core Exceptions

```python
from social_integrator.core.platform import (
    PlatformError,
    RateLimitError,
    AuthenticationError
)
```

- `PlatformError`: Base class for platform-specific errors
- `RateLimitError`: Raised when rate limits are exceeded
- `AuthenticationError`: Raised for authentication failures

## Basic Error Handling

```python
from social_integrator import SocialIntegrator, SocialPost

async def handle_errors():
    integrator = SocialIntegrator()
    post = SocialPost(content="Test post")

    try:
        await integrator.post("twitter", post)
    except RateLimitError as e:
        print(f"Rate limit exceeded: {e}")
        # Handle rate limiting
    except AuthenticationError as e:
        print(f"Authentication failed: {e}")
        # Re-authenticate
    except PlatformError as e:
        print(f"Platform error: {e}")
        # Handle other platform errors
```

## Advanced Error Handling

### Retry Logic

```python
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type
)

@retry(
    retry=retry_if_exception_type(RateLimitError),
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=4, max=10)
)
async def post_with_retry():
    await integrator.post("twitter", post)
```

### Error Recovery

```python
async def recover_from_error():
    try:
        await integrator.post("twitter", post)
    except AuthenticationError:
        # Re-authenticate
        await integrator.auth_manager.revoke_token("twitter")
        token = await integrator.auth_manager.get_valid_token("twitter")
        # Retry with new token
        await integrator.post("twitter", post)
```

## Platform-Specific Errors

### Twitter Errors

```python
try:
    await integrator.post("twitter", post)
except PlatformError as e:
    if "duplicate" in str(e):
        # Handle duplicate tweet
        pass
    elif "media_ids" in str(e):
        # Handle media upload error
        pass
```

## Best Practices

1. Always catch specific exceptions
2. Implement appropriate retry logic
3. Log errors for debugging
4. Handle rate limits gracefully
5. Implement proper error recovery

## Logging

```python
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("social_integrator")

try:
    await integrator.post("twitter", post)
except Exception as e:
    logger.error(f"Error posting to Twitter: {e}", exc_info=True)
```
