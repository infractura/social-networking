import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from social_integrator.platforms.twitter import TwitterAPI
from social_integrator.core.platform import SocialPost
from social_integrator.utils.rate_limiting import AsyncBatcher

@pytest.fixture
def twitter_api():
    """Create a TwitterAPI instance."""
    return TwitterAPI(auth_token="test_token")

@pytest.mark.asyncio
async def test_batch_post_processing(twitter_api):
    """Test batch processing of posts."""
    # Create test posts
    posts = [
        SocialPost(content=f"Test post {i}")
        for i in range(5)
    ]

    # Mock API responses
    mock_responses = [
        {"data": {"id": f"tweet_{i}"}}
        for i in range(5)
    ]

    # Create batcher
    batcher = AsyncBatcher(
        batch_size=2,
        flush_interval=0.1,
        rate_limiter=twitter_api.rate_limiter
    )

    # Mock post method
    twitter_api.post = AsyncMock(side_effect=mock_responses)

    # Process posts in batches
    results = []
    for post in posts:
        await batcher.add(post)
        if len(batcher.batch) >= batcher.batch_size:
            await batcher.flush()

    # Flush remaining posts
    await batcher.flush()

    # Verify all posts were processed
    assert twitter_api.post.call_count == 5

@pytest.mark.asyncio
async def test_batch_media_upload(twitter_api):
    """Test batch processing of media uploads."""
    # Create post with multiple media
    post = SocialPost(
        content="Test post with media",
        media_urls=[
            "https://example.com/image1.jpg",
            "https://example.com/image2.jpg"
        ]
    )

    # Mock media upload responses
    mock_upload_responses = [
        {"media_id_string": f"media_{i}"}
        for i in range(2)
    ]

    # Mock upload method
    twitter_api._upload_media = AsyncMock(return_value=["media_1", "media_2"])

    # Process post with media
    await twitter_api.post(post)

    # Verify media was uploaded
    twitter_api._upload_media.assert_called_once_with(post.media_urls)

@pytest.mark.asyncio
async def test_batch_error_handling(twitter_api):
    """Test error handling in batch processing."""
    # Create batcher
    batcher = AsyncBatcher(
        batch_size=2,
        flush_interval=0.1,
        rate_limiter=twitter_api.rate_limiter
    )

    # Mock post method to raise error
    twitter_api.post = AsyncMock(side_effect=ValueError("Test error"))

    # Add post to batch
    post = SocialPost(content="Test post")

    # Error should be caught and logged
    with pytest.raises(ValueError, match="Test error"):
        await batcher.add(post)
        await batcher.flush()
