# Twitter Integration Guide

Detailed guide for integrating with Twitter using Social Integrator.

## Prerequisites

1. Twitter Developer Account
2. Twitter API v2 Access
3. OAuth 2.0 App Credentials

## Features

- Post tweets with text and media
- Delete tweets
- Get tweet metrics
- Handle rate limits

## Basic Usage

```python
from social_integrator import SocialIntegrator, SocialPost

async def twitter_example():
    integrator = SocialIntegrator()
    
    # Configure Twitter
    integrator.configure_twitter(
        client_id="your_client_id",
        client_secret="your_client_secret"
    )
    
    # Create a tweet
    post = SocialPost(
        content="Hello Twitter! #SocialIntegrator",
        media_urls=["https://example.com/image.jpg"],
        metadata={
            "tags": ["hello", "twitter"]
        }
    )
    
    async with integrator:
        # Post tweet
        result = await integrator.post("twitter", post)
        tweet_id = result["data"]["id"]
        
        # Get metrics
        metrics = await integrator.get_metrics("twitter", tweet_id)
        print(f"Tweet metrics: {metrics}")
        
        # Delete tweet
        deleted = await integrator.delete_post("twitter", tweet_id)
        print(f"Tweet deleted: {deleted}")
```

## Media Handling

Twitter supports various media types:

```python
# Tweet with multiple media
post = SocialPost(
    content="Check out these images!",
    media_urls=[
        "https://example.com/image1.jpg",
        "https://example.com/image2.jpg"
    ]
)
```

## Rate Limits

Twitter API v2 rate limits:

- Tweet creation: 300 per 15 minutes
- Tweet deletion: 300 per 15 minutes
- Tweet lookup: 300 per 15 minutes

Configure custom limits:

```python
from social_integrator.core.config import TwitterConfig

config = TwitterConfig(
    rate_limit_calls=100,
    rate_limit_period=900.0  # 15 minutes
)
```

## Error Handling

Handle Twitter-specific errors:

```python
from social_integrator.core.platform import PlatformError

try:
    await integrator.post("twitter", post)
except PlatformError as e:
    if "duplicate" in str(e):
        print("Duplicate tweet")
    else:
        print(f"Twitter error: {e}")
```

## Best Practices

1. Follow Twitter's content guidelines
2. Handle rate limits appropriately
3. Implement proper error handling
4. Use appropriate scopes for authentication
5. Monitor API usage and metrics
