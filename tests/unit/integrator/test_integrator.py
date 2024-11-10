import pytest
from unittest.mock import AsyncMock, MagicMock

from social_integrator import SocialIntegrator, SocialPost
from social_integrator.core.platform import PlatformError

@pytest.fixture
def mock_twitter_provider():
    """Create a mock Twitter auth provider."""
    provider = AsyncMock()
    provider.authenticate.return_value = MagicMock(
        access_token="mock_token",
        platform="twitter"
    )
    return provider

@pytest.mark.asyncio
async def test_integrator_initialization():
    """Test basic integrator initialization."""
    integrator = SocialIntegrator()
    assert integrator.auth_manager is not None
    assert integrator.platforms == {}

@pytest.mark.asyncio
async def test_twitter_configuration(mock_twitter_provider):
    """Test Twitter platform configuration."""
    integrator = SocialIntegrator()
    
    # Configure Twitter
    integrator.configure_twitter(
        client_id="test_id",
        client_secret="test_secret"
    )
    
    # Verify provider registration
    assert "twitter" in integrator.auth_manager.providers

@pytest.mark.asyncio
async def test_post_lifecycle():
    """Test complete post lifecycle."""
    integrator = SocialIntegrator()
    
    # Mock platform
    mock_platform = AsyncMock()
    mock_platform.post.return_value = {"data": {"id": "123"}}
    mock_platform.get_metrics.return_value = {"likes": 10}
    mock_platform.delete_post.return_value = True
    
    integrator.platforms["twitter"] = mock_platform
    
    # Create post
    post = SocialPost(content="Test post")
    
    async with integrator:
        # Post
        result = await integrator.post("twitter", post)
        assert result["data"]["id"] == "123"
        
        # Get metrics
        metrics = await integrator.get_metrics("twitter", "123")
        assert metrics["likes"] == 10
        
        # Delete
        deleted = await integrator.delete_post("twitter", "123")
        assert deleted is True

@pytest.mark.asyncio
async def test_error_handling():
    """Test error handling in integrator."""
    integrator = SocialIntegrator()
    
    # Mock platform that raises errors
    mock_platform = AsyncMock()
    mock_platform.post.side_effect = PlatformError("Post failed")
    
    integrator.platforms["twitter"] = mock_platform
    
    # Test error propagation
    post = SocialPost(content="Test post")
    
    async with integrator:
        with pytest.raises(PlatformError, match="Post failed"):
            await integrator.post("twitter", post)

@pytest.mark.asyncio
async def test_platform_validation():
    """Test platform validation."""
    integrator = SocialIntegrator()
    post = SocialPost(content="Test post")
    
    # Test unsupported platform
    async with integrator:
        with pytest.raises(ValueError, match="Unsupported platform"):
            await integrator.post("unsupported", post)
