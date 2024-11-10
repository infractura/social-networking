# Social Integrator

A Python library for programmatic social networking integration.

## Features

- 🔄 Unified interface for multiple social media platforms
- 🔐 Secure authentication handling
- ⚡ Asynchronous API support
- 🛡️ Built-in rate limiting
- 🔍 Comprehensive error handling
- 📊 Engagement metrics tracking

## Quick Example

Here's a simple example of how to use Social Integrator:

```python
import asyncio
from social_integrator import SocialIntegrator, SocialPost

async def main():
    # Initialize the integrator
    integrator = SocialIntegrator()
    
    # Configure Twitter
    integrator.configure_twitter(
        client_id="your_client_id",
        client_secret="your_client_secret"
    )
    
    # Create a post
    post = SocialPost(
        content="Hello from Social Integrator!",
        media_urls=["https://example.com/image.jpg"]
    )
    
    async with integrator:
        # Post to Twitter
        result = await integrator.post("twitter", post)
        print(f"Posted to Twitter: {result}")
        
        # Get metrics after a delay
        await asyncio.sleep(60)
        metrics = await integrator.get_metrics("twitter", result["data"]["id"])
        print(f"Post metrics: {metrics}")

if __name__ == "__main__":
    asyncio.run(main())
```

## Installation

Install using pip:

```bash
pip install social-integrator
```

## Documentation

For more detailed documentation, please visit the [User Guide](user-guide/index.md).
