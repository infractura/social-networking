# Core API Reference

Reference documentation for the core components of Social Integrator.

## SocialPost

```python
class SocialPost:
    """Base model for social media posts."""

    def __init__(
        self,
        content: str,
        media_urls: List[str] = [],
        metadata: Dict[str, Any] = {}
    ):
        """Initialize a social post.

        Args:
            content: The text content of the post
            media_urls: List of URLs to media attachments
            metadata: Additional platform-specific metadata
        """
```

## SocialPlatform

```python
class SocialPlatform(ABC):
    """Abstract base class for social media platform integrations."""

    @abstractmethod
    async def post(self, post: SocialPost) -> Dict[str, Any]:
        """Post content to the platform.

        Args:
            post: The post content and metadata

        Returns:
            Dict containing the response from the platform
        """

    @abstractmethod
    async def delete_post(self, post_id: str) -> bool:
        """Delete a post from the platform.

        Args:
            post_id: Platform-specific post identifier

        Returns:
            True if deletion was successful
        """

    @abstractmethod
    async def get_metrics(self, post_id: str) -> Dict[str, Any]:
        """Get engagement metrics for a post.

        Args:
            post_id: Platform-specific post identifier

        Returns:
            Dictionary of metrics (likes, shares, etc.)
        """
```

## Exceptions

### PlatformError

```python
class PlatformError(Exception):
    """Base class for platform-specific errors."""
    pass
```

### RateLimitError

```python
class RateLimitError(PlatformError):
    """Raised when platform rate limits are exceeded."""
    pass
```

### AuthenticationError

```python
class AuthenticationError(PlatformError):
    """Raised when authentication fails."""
    pass
```
