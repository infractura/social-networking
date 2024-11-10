import aiohttp
from typing import Dict, Any, Optional
import json

from ..core.platform import (
    SocialPlatform,
    SocialPost,
    PlatformError,
    RateLimitError
)
from ..utils.rate_limiting import with_rate_limiting
from ..core.config import TwitterConfig, get_platform_config

class TwitterAPI(SocialPlatform):
    """Twitter API implementation."""
    
    def __init__(self, auth_token: str):
        """Initialize Twitter API client.
        
        Args:
            auth_token: Bearer token for authentication
        """
        super().__init__(auth_token=auth_token)
        
        # Get configuration
        config = get_platform_config("twitter")
        if not isinstance(config, TwitterConfig):
            config = TwitterConfig()
        self.config = config
    
    def _initialize(self) -> None:
        """Initialize HTTP session."""
        self.session = aiohttp.ClientSession(
            headers={
                "Authorization": f"Bearer {self.auth_token}",
                "Content-Type": "application/json"
            }
        )
    
    async def close(self) -> None:
        """Close HTTP session."""
        if hasattr(self, 'session'):
            await self.session.close()
    
    def _handle_error(self, status: int, data: Dict[str, Any]) -> None:
        """Handle error response.
        
        Args:
            status: HTTP status code
            data: Response data
            
        Raises:
            RateLimitError: If rate limited
            PlatformError: For other errors
        """
        if status == 429:  # Rate limit
            retry_after = int(data.get("retry_after", 60))
            raise RateLimitError(
                "Twitter API rate limit exceeded",
                retry_after=retry_after
            )
        
        message = data.get("detail", "Unknown error")
        if isinstance(data.get("errors"), list):
            message = data["errors"][0].get("message", message)
        
        raise PlatformError(f"Twitter API error: {message}")
    
    @with_rate_limiting(calls=300, period=900)
    async def post(self, post: SocialPost) -> Dict[str, Any]:
        """Create a tweet.
        
        Args:
            post: Tweet content and metadata
            
        Returns:
            Tweet data including ID
        """
        data = {
            "text": post.content,
        }
        
        if post.media_urls:
            # TODO: Implement media upload
            pass
        
        async with self.session.post(
            f"{self.config.api_base_url}/tweets",
            json=data
        ) as resp:
            resp_data = await resp.json()
            
            if not resp.ok:
                self._handle_error(resp.status, resp_data)
            
            return resp_data
    
    @with_rate_limiting(calls=300, period=900)
    async def delete_post(self, post_id: str) -> bool:
        """Delete a tweet.
        
        Args:
            post_id: Tweet ID
            
        Returns:
            True if deletion was successful
        """
        async with self.session.delete(
            f"{self.config.api_base_url}/tweets/{post_id}"
        ) as resp:
            if resp.status == 404:
                return False
            
            if not resp.ok:
                resp_data = await resp.json()
                self._handle_error(resp.status, resp_data)
            
            return True
    
    @with_rate_limiting(calls=300, period=900)
    async def get_post(self, post_id: str) -> Dict[str, Any]:
        """Get tweet details.
        
        Args:
            post_id: Tweet ID
            
        Returns:
            Tweet data
        """
        async with self.session.get(
            f"{self.config.api_base_url}/tweets/{post_id}"
        ) as resp:
            if resp.status == 404:
                return {}
            
            resp_data = await resp.json()
            if not resp.ok:
                self._handle_error(resp.status, resp_data)
            
            return resp_data
    
    @with_rate_limiting(calls=300, period=900)
    async def get_metrics(self, post_id: str) -> Dict[str, Any]:
        """Get tweet metrics.
        
        Args:
            post_id: Tweet ID
            
        Returns:
            Tweet metrics
        """
        params = {
            "tweet.fields": "public_metrics"
        }
        
        async with self.session.get(
            f"{self.config.api_base_url}/tweets/{post_id}",
            params=params
        ) as resp:
            resp_data = await resp.json()
            
            if not resp.ok:
                self._handle_error(resp.status, resp_data)
            
            metrics = resp_data["data"].get("public_metrics", {})
            return {
                "likes": metrics.get("like_count", 0),
                "retweets": metrics.get("retweet_count", 0),
                "replies": metrics.get("reply_count", 0),
                "quotes": metrics.get("quote_count", 0)
            }
