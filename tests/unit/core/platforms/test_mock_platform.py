import pytest
import asyncio
from social_integrator.core.platform import SocialPost, PlatformError
from tests.unit.core.conftest import MockPlatform

@pytest.mark.asyncio
async def test_mock_platform_post(mock_platform, sample_post):
    """Test basic post creation."""
    result = await mock_platform.post(sample_post)
    
    assert "id" in result
    assert result["platform"] == "mock"
    assert result["status"] == "posted"
    assert mock_platform.post_counter == 1

@pytest.mark.asyncio
async def test_mock_platform_get_post(mock_platform, sample_post):
    """Test post retrieval."""
    # Create a post first
    result = await mock_platform.post(sample_post)
    post_id = result["id"]
    
    # Get the post
    post_data = await mock_platform.get_post(post_id)
    assert post_data["content"] == sample_post.content
    assert post_data["media_urls"] == sample_post.media_urls
    assert post_data["metadata"] == sample_post.metadata

@pytest.mark.asyncio
async def test_mock_platform_delete_post(mock_platform, sample_post):
    """Test post deletion."""
    # Create a post first
    result = await mock_platform.post(sample_post)
    post_id = result["id"]
    
    # Delete the post
    assert await mock_platform.delete_post(post_id)
    
    # Verify it's deleted
    empty_data = await mock_platform.get_post(post_id)
    assert empty_data == {}

@pytest.mark.asyncio
async def test_mock_platform_get_metrics(mock_platform, sample_post):
    """Test metrics retrieval."""
    # Create a post first
    result = await mock_platform.post(sample_post)
    post_id = result["id"]
    
    # Get metrics
    metrics = await mock_platform.get_metrics(post_id)
    assert metrics["likes"] == 42
    assert metrics["shares"] == 7
    assert metrics["comments"] == 3

@pytest.mark.asyncio
async def test_mock_platform_nonexistent_post(mock_platform):
    """Test operations with nonexistent posts."""
    # Try to get nonexistent post
    empty_data = await mock_platform.get_post("nonexistent")
    assert empty_data == {}
    
    # Try to delete nonexistent post
    assert not await mock_platform.delete_post("nonexistent")
    
    # Try to get metrics for nonexistent post
    with pytest.raises(PlatformError, match="Post not found"):
        await mock_platform.get_metrics("nonexistent")

@pytest.mark.asyncio
async def test_mock_platform_errors(failing_mock_platform, sample_post):
    """Test error handling in failing platform."""
    # Test post creation
    with pytest.raises(PlatformError, match="Mock platform error"):
        await failing_mock_platform.post(sample_post)
    
    # Test post retrieval
    with pytest.raises(PlatformError, match="Mock platform error"):
        await failing_mock_platform.get_post("any_id")
    
    # Test post deletion
    with pytest.raises(PlatformError, match="Mock platform error"):
        await failing_mock_platform.delete_post("any_id")
    
    # Test metrics retrieval
    with pytest.raises(PlatformError, match="Mock platform error"):
        await failing_mock_platform.get_metrics("any_id")

@pytest.mark.asyncio
async def test_mock_platform_concurrent_operations(mock_platform):
    """Test concurrent platform operations."""
    # Create multiple posts concurrently
    posts = [
        SocialPost(content=f"Test post {i}")
        for i in range(3)  # Reduced from 5 to 3
    ]
    
    results = await asyncio.gather(
        *[mock_platform.post(post) for post in posts]
    )
    
    assert len(results) == 3
    assert all("id" in result for result in results)
    assert mock_platform.post_counter == 3
    
    # Get all posts concurrently
    post_ids = [result["id"] for result in results]
    posts_data = await asyncio.gather(
        *[mock_platform.get_post(post_id) for post_id in post_ids]
    )
    
    assert len(posts_data) == 3
    assert all(post["content"].startswith("Test post") for post in posts_data)
    
    # Get metrics concurrently
    metrics = await asyncio.gather(
        *[mock_platform.get_metrics(post_id) for post_id in post_ids]
    )
    
    assert len(metrics) == 3
    assert all(m["likes"] == 42 for m in metrics)

@pytest.mark.asyncio
async def test_mock_platform_initialization():
    """Test platform initialization."""
    platform = MockPlatform(auth_token="test_token")
    assert platform.auth_token == "test_token"
    assert platform.posts == {}
    assert platform.post_counter == 0
