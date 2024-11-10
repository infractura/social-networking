import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from social_integrator.platforms.twitter import TwitterAPI
from social_integrator.core.platform import PlatformError, SocialPost

@pytest.fixture
def twitter_api():
    """Create a TwitterAPI instance."""
    return TwitterAPI(auth_token="test_token")

@pytest.mark.asyncio
async def test_content_length_validation(twitter_api):
    """Test tweet content length validation."""
    # Test maximum allowed length
    max_content = "x" * 280
    post = SocialPost(content=max_content)

    # Should not raise error
    await twitter_api._validate_post(post)

    # Test content too long
    long_content = "x" * 281
    post = SocialPost(content=long_content)

    with pytest.raises(PlatformError, match="Tweet content exceeds 280 characters"):
        await twitter_api._validate_post(post)

@pytest.mark.asyncio
async def test_content_formatting(twitter_api):
    """Test tweet content formatting."""
    # Test URL shortening
    post = SocialPost(
        content="Check out https://www.example.com/very/long/url/that/should/be/shortened"
    )

    formatted = await twitter_api._format_content(post)
    assert len(formatted) < len(post.content)  # URL should be shortened

    # Test hashtag formatting
    post = SocialPost(
        content="Test post",
        metadata={"tags": ["test", "social"]}
    )

    formatted = await twitter_api._format_content(post)
    assert "#test" in formatted
    assert "#social" in formatted

@pytest.mark.asyncio
async def test_content_sanitization(twitter_api):
    """Test tweet content sanitization."""
    # Test newline normalization
    post = SocialPost(content="Line 1\\n\\n\\nLine 2")
    formatted = await twitter_api._format_content(post)
    assert formatted == "Line 1\\n\\nLine 2"  # Multiple newlines reduced to two

    # Test whitespace trimming
    post = SocialPost(content="  Test   post  ")
    formatted = await twitter_api._format_content(post)
    assert formatted == "Test post"

@pytest.mark.asyncio
async def test_content_validation_rules(twitter_api):
    """Test various content validation rules."""
    # Test empty content
    post = SocialPost(content="")
    with pytest.raises(PlatformError, match="Tweet content cannot be empty"):
        await twitter_api._validate_post(post)

    # Test whitespace-only content
    post = SocialPost(content="   \\n   ")
    with pytest.raises(PlatformError, match="Tweet content cannot be empty"):
        await twitter_api._validate_post(post)

    # Test duplicate hashtags
    post = SocialPost(
        content="Test",
        metadata={"tags": ["test", "test"]}  # Duplicate tag
    )
    formatted = await twitter_api._format_content(post)
    assert formatted.count("#test") == 1  # Duplicate tag should be removed

@pytest.mark.asyncio
async def test_mention_handling(twitter_api):
    """Test handling of @mentions."""
    # Test mention at start
    post = SocialPost(content="@user Hello")
    formatted = await twitter_api._format_content(post)
    assert formatted == ".@user Hello"  # Dot added to ensure visibility

    # Test mention in middle
    post = SocialPost(content="Hello @user!")
    formatted = await twitter_api._format_content(post)
    assert formatted == "Hello @user!"  # No modification needed
