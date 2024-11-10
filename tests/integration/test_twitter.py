import os
import pytest
from dotenv import load_dotenv

from social_integrator import SocialIntegrator, SocialPost
from social_integrator.core.platform import PlatformError

# Load environment variables for testing
load_dotenv()

@pytest.fixture
async def twitter_integrator():
    """Create a configured Twitter integrator."""
    integrator = SocialIntegrator()
    integrator.configure_twitter(
        client_id=os.getenv("SOCIAL_TWITTER__CLIENT_ID"),
        client_secret=os.getenv("SOCIAL_TWITTER__CLIENT_SECRET")
    )
    return integrator

@pytest.mark.integration
@pytest.mark.asyncio
async def test_twitter_post_lifecycle(twitter_integrator):
    """Test the complete lifecycle of a Twitter post."""
    post = SocialPost(
        content=f"Test post from Social Integrator {os.urandom(4).hex()}",
        metadata={"test": True}
    )

    async with twitter_integrator as integrator:
        # Create post
        result = await integrator.post("twitter", post)
        assert "data" in result
        assert "id" in result["data"]

        post_id = result["data"]["id"]

        # Get metrics
        metrics = await integrator.get_metrics("twitter", post_id)
        assert isinstance(metrics, dict)

        # Delete post
        deleted = await integrator.delete_post("twitter", post_id)
        assert deleted is True

@pytest.mark.integration
@pytest.mark.asyncio
async def test_twitter_rate_limiting(twitter_integrator):
    """Test rate limiting behavior."""
    posts = [
        SocialPost(content=f"Rate limit test {i} {os.urandom(4).hex()}")
        for i in range(5)
    ]

    post_ids = []
    async with twitter_integrator as integrator:
        # Post multiple tweets
        for post in posts:
            result = await integrator.post("twitter", post)
            post_ids.append(result["data"]["id"])

        # Clean up
        for post_id in post_ids:
            await integrator.delete_post("twitter", post_id)

@pytest.mark.integration
@pytest.mark.asyncio
async def test_twitter_error_handling(twitter_integrator):
    """Test error handling."""
    async with twitter_integrator as integrator:
        # Test non-existent post
        with pytest.raises(PlatformError):
            await integrator.get_metrics("twitter", "nonexistent_id")

        # Test duplicate post
        post = SocialPost(content=f"Duplicate test {os.urandom(4).hex()}")
        result = await integrator.post("twitter", post)
        with pytest.raises(PlatformError):
            await integrator.post("twitter", post)  # Same content

        # Clean up
        await integrator.delete_post("twitter", result["data"]["id"])
