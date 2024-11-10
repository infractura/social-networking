# Social Integrator

A Python library for programmatic social networking integration.

[![PyPI version](https://badge.fury.io/py/social-integrator.svg)](https://badge.fury.io/py/social-integrator)
[![CI](https://github.com/yourusername/social-integrator/actions/workflows/ci.yml/badge.svg)](https://github.com/yourusername/social-integrator/actions/workflows/ci.yml)
[![Documentation Status](https://readthedocs.org/projects/social-integrator/badge/?version=latest)](https://social-integrator.readthedocs.io/en/latest/?badge=latest)
[![codecov](https://codecov.io/gh/yourusername/social-integrator/branch/main/graph/badge.svg)](https://codecov.io/gh/yourusername/social-integrator)

## Features

- 🔄 Unified interface for multiple social media platforms
- 🔐 Secure authentication handling
- ⚡ Asynchronous API support
- 🛡️ Built-in rate limiting
- 🔍 Comprehensive error handling
- 📊 Engagement metrics tracking

## Installation

```bash
pip install social-integrator
```

## Quick Start

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
        content="Hello from Social Integrator! 🌍",
        media_urls=["https://example.com/image.jpg"],
        metadata={"tags": ["hello", "social"]}
    )
    
    async with integrator:
        # Post to Twitter
        result = await integrator.post("twitter", post)
        print(f"Posted to Twitter: {result}")
        
        # Get metrics
        metrics = await integrator.get_metrics("twitter", result["data"]["id"])
        print(f"Post metrics: {metrics}")

if __name__ == "__main__":
    asyncio.run(main())
```

## Documentation

Full documentation is available at [social-integrator.readthedocs.io](https://social-integrator.readthedocs.io/).

## Development

### Setup

```bash
git clone https://github.com/yourusername/social-integrator.git
cd social-integrator
pip install -e ".[dev]"
pre-commit install
```

### Running Tests

```bash
pytest
```

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
