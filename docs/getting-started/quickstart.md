# Quick Start Guide

This guide will help you get started with Social Integrator quickly.

## Basic Setup

```python
from social_integrator import SocialIntegrator, SocialPost

# Initialize the integrator
integrator = SocialIntegrator()

# Configure Twitter
integrator.configure_twitter(
    client_id="your_client_id",
    client_secret="your_client_secret"
)
```

## Creating and Posting Content

```python
import asyncio

async def post_content():
    # Create a post
    post = SocialPost(
        content="Hello, Social World! 🌍",
        media_urls=["https://example.com/image.jpg"],
        metadata={"tags": ["hello", "social"]}
    )

    async with integrator:
        # Post to Twitter
        result = await integrator.post("twitter", post)
        print(f"Posted to Twitter: {result}")

        # Get post metrics
        post_id = result["data"]["id"]
        metrics = await integrator.get_metrics("twitter", post_id)
        print(f"Post metrics: {metrics}")

asyncio.run(post_content())
```

## Error Handling

```python
from social_integrator.core.platform import PlatformError, RateLimitError

async def post_with_error_handling():
    try:
        async with integrator:
            result = await integrator.post("twitter", post)
    except RateLimitError:
        print("Rate limit exceeded. Please wait and try again.")
    except PlatformError as e:
        print(f"Platform error: {e}")
```

## Next Steps

- Learn about [authentication](../user-guide/authentication.md)
- Explore [rate limiting](../user-guide/rate-limiting.md)
- Check platform-specific guides:
  - [Twitter Integration](../user-guide/platforms/twitter.md)
