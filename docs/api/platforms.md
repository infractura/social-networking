# Platforms API Reference

Reference documentation for platform-specific implementations.

## Twitter

### TwitterAPI

```python
class TwitterAPI(SocialPlatform):
    """Twitter platform implementation using Twitter API v2."""

    def __init__(
        self,
        auth_token: str,
        api_base_url: Optional[str] = None
    ):
        """Initialize Twitter API client.

        Args:
            auth_token: OAuth 2.0 access token
            api_base_url: Optional custom API base URL
        """

    async def post(self, post: SocialPost) -> Dict[str, Any]:
        """Post a tweet.

        Args:
            post: Tweet content and metadata

        Returns:
            Dict containing tweet data

        Raises:
            PlatformError: If tweet creation fails
            RateLimitError: If rate limit is exceeded
        """

    async def delete_post(self, post_id: str) -> bool:
        """Delete a tweet.

        Args:
            post_id: Tweet ID

        Returns:
            True if deletion was successful

        Raises:
            PlatformError: If tweet deletion fails
        """

    async def get_metrics(self, post_id: str) -> Dict[str, Any]:
        """Get tweet metrics.

        Args:
            post_id: Tweet ID

        Returns:
            Dict containing engagement metrics

        Raises:
            PlatformError: If metrics retrieval fails
        """

    async def _upload_media(self, media_urls: List[str]) -> List[str]:
        """Upload media to Twitter.

        Args:
            media_urls: List of media URLs to upload

        Returns:
            List of Twitter media IDs
        """
```

### Configuration

```python
class TwitterConfig(PlatformConfig):
    """Twitter-specific configuration."""

    api_base_url: str = "https://api.twitter.com/2"
    rate_limit_calls: int = 300
    rate_limit_period: float = 900.0
    media_upload_url: str = "https://upload.twitter.com/1.1/media/upload.json"
```
