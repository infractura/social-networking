from typing import Dict, Optional, Type
import asyncio
from pathlib import Path

from .core.platform import SocialPlatform, SocialPost
from .core.config import Settings, get_platform_config
from .auth.auth_manager import AuthManager
from .platforms.twitter import TwitterAPI
from .auth.providers.twitter import TwitterAuthProvider


class SocialIntegrator:
    """Main interface for social media integration."""
    
    def __init__(self):
        """Initialize the social integrator."""
        self.auth_manager = AuthManager()
        self.platforms: Dict[str, SocialPlatform] = {}
        self._platform_classes: Dict[str, Type[SocialPlatform]] = {
            "twitter": TwitterAPI,
        }
    
    def configure_twitter(
        self,
        client_id: str,
        client_secret: str,
        redirect_uri: Optional[str] = None
    ) -> None:
        """Configure Twitter authentication.
        
        Args:
            client_id: Twitter API client ID
            client_secret: Twitter API client secret
            redirect_uri: OAuth redirect URI (default: http://localhost:8080/callback)
        """
        if not redirect_uri:
            redirect_uri = "http://localhost:8080/callback"
        
        provider = TwitterAuthProvider(
            client_id=client_id,
            client_secret=client_secret,
            redirect_uri=redirect_uri
        )
        self.auth_manager.register_provider("twitter", provider)
    
    async def get_platform(self, platform_name: str) -> SocialPlatform:
        """Get or create a platform instance.
        
        Args:
            platform_name: Name of the platform ("twitter", etc.)
            
        Returns:
            Platform instance
        """
        if platform_name in self.platforms:
            return self.platforms[platform_name]
        
        if platform_name not in self._platform_classes:
            raise ValueError(f"Unsupported platform: {platform_name}")
        
        # Get authentication token
        token_info = await self.auth_manager.get_valid_token(platform_name)
        
        # Create platform instance
        platform_class = self._platform_classes[platform_name]
        platform = platform_class(auth_token=token_info.access_token)
        self.platforms[platform_name] = platform
        
        return platform
    
    async def post(self, platform_name: str, post: SocialPost) -> Dict[str, str]:
        """Post content to a social media platform.
        
        Args:
            platform_name: Name of the platform
            post: Post content and metadata
            
        Returns:
            Platform-specific response
        """
        platform = await self.get_platform(platform_name)
        return await platform.post(post)
    
    async def delete_post(self, platform_name: str, post_id: str) -> bool:
        """Delete a post from a platform.
        
        Args:
            platform_name: Name of the platform
            post_id: Platform-specific post identifier
            
        Returns:
            True if deletion was successful
        """
        platform = await self.get_platform(platform_name)
        return await platform.delete_post(post_id)
    
    async def get_metrics(self, platform_name: str, post_id: str) -> Dict[str, int]:
        """Get engagement metrics for a post.
        
        Args:
            platform_name: Name of the platform
            post_id: Platform-specific post identifier
            
        Returns:
            Dictionary of metrics
        """
        platform = await self.get_platform(platform_name)
        return await platform.get_metrics(post_id)
    
    async def close(self) -> None:
        """Close all platform connections."""
        for platform in self.platforms.values():
            if hasattr(platform, 'close'):
                await platform.close()
    
    async def __aenter__(self) -> "SocialIntegrator":
        """Context manager entry."""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit."""
        await self.close()


# Example usage
async def main():
    integrator = SocialIntegrator()
    
    # Configure Twitter
    integrator.configure_twitter(
        client_id="YOUR_CLIENT_ID",
        client_secret="YOUR_CLIENT_SECRET"
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
        post_id = result["data"]["id"]
        await asyncio.sleep(60)  # Wait for engagement
        metrics = await integrator.get_metrics("twitter", post_id)
        print(f"Post metrics: {metrics}")


if __name__ == "__main__":
    asyncio.run(main())
