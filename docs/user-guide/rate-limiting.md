# Rate Limiting Guide

Understanding and working with rate limits in Social Integrator.

## Overview

Social Integrator provides built-in rate limiting features:

- Token bucket algorithm implementation
- Automatic retry handling
- Platform-specific rate limit configurations
- Batch processing support

## Basic Usage

Rate limiting is automatically applied to all API calls:

```python
from social_integrator import SocialIntegrator, SocialPost

async def example_rate_limited_posts():
    integrator = SocialIntegrator()
    
    # These posts will be automatically rate limited
    posts = [
        SocialPost(content=f"Post {i}")
        for i in range(10)
    ]
    
    async with integrator:
        for post in posts:
            await integrator.post("twitter", post)
```

## Custom Rate Limits

You can customize rate limits per platform:

```python
from social_integrator.core.config import TwitterConfig

twitter_config = TwitterConfig(
    rate_limit_calls=100,  # calls per period
    rate_limit_period=900.0  # 15 minutes
)

integrator = SocialIntegrator()
integrator.configure_twitter(
    client_id="your_client_id",
    client_secret="your_client_secret",
    config=twitter_config
)
```

## Batch Processing

For multiple operations, use batch processing:

```python
from social_integrator.utils.rate_limiting import AsyncBatcher

async def batch_example():
    batcher = AsyncBatcher(
        batch_size=10,
        flush_interval=60.0,
        rate_limiter=integrator.platforms["twitter"].rate_limiter
    )
    
    # Add items to batch
    for i in range(100):
        await batcher.add(f"Item {i}")
    
    # Flush remaining items
    await batcher.flush()
```

## Error Handling

Handle rate limit errors gracefully:

```python
from social_integrator.core.platform import RateLimitError

async def handle_rate_limits():
    try:
        await integrator.post("twitter", post)
    except RateLimitError as e:
        print(f"Rate limited: {e}")
        # Handle rate limit (e.g., wait, queue, or skip)
```

## Best Practices

1. Use batch processing for multiple operations
2. Implement exponential backoff for retries
3. Monitor rate limit usage
4. Cache responses when possible
5. Use appropriate rate limits for your use case
