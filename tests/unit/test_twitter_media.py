import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import aiohttp
import asyncio

from social_integrator.platforms.twitter import TwitterAPI
from social_integrator.core.platform import PlatformError, SocialPost

@pytest.fixture
def twitter_api():
    """Create a TwitterAPI instance."""
    return TwitterAPI(auth_token="test_token")

@pytest.mark.asyncio
async def test_media_upload(twitter_api):
    """Test media upload functionality."""
    # Mock successful media download
    mock_media_response = MagicMock()
    mock_media_response.read = AsyncMock(return_value=b"fake_image_data")

    # Mock successful media upload
    mock_upload_response = MagicMock()
    mock_upload_response.ok = True
    mock_upload_response.json = AsyncMock(return_value={
        "media_id_string": "123456789"
    })

    # Mock session methods
    mock_session = AsyncMock()
    mock_session.get.return_value.__aenter__.return_value = mock_media_response
    mock_session.post.return_value.__aenter__.return_value = mock_upload_response

    with patch.object(twitter_api, "session", mock_session):
        media_ids = await twitter_api._upload_media([
            "https://example.com/image.jpg"
        ])

        assert len(media_ids) == 1
        assert media_ids[0] == "123456789"

@pytest.mark.asyncio
async def test_media_download_error(twitter_api):
    """Test handling of media download errors."""
    # Mock failed media download
    mock_session = AsyncMock()
    mock_session.get.side_effect = aiohttp.ClientError("Download failed")

    with patch.object(twitter_api, "session", mock_session):
        with pytest.raises(PlatformError, match="Failed to download media"):
            await twitter_api._upload_media([
                "https://example.com/image.jpg"
            ])

@pytest.mark.asyncio
async def test_media_upload_error(twitter_api):
    """Test handling of media upload errors."""
    # Mock successful download but failed upload
    mock_media_response = MagicMock()
    mock_media_response.read = AsyncMock(return_value=b"fake_image_data")

    mock_upload_response = MagicMock()
    mock_upload_response.ok = False
    mock_upload_response.json = AsyncMock(return_value={
        "errors": [{"message": "Upload failed"}]
    })

    mock_session = AsyncMock()
    mock_session.get.return_value.__aenter__.return_value = mock_media_response
    mock_session.post.return_value.__aenter__.return_value = mock_upload_response

    with patch.object(twitter_api, "session", mock_session):
        with pytest.raises(PlatformError, match="Upload failed"):
            await twitter_api._upload_media([
                "https://example.com/image.jpg"
            ])

@pytest.mark.asyncio
async def test_multiple_media_upload(twitter_api):
    """Test uploading multiple media files."""
    # Mock successful media operations
    mock_media_response = MagicMock()
    mock_media_response.read = AsyncMock(return_value=b"fake_image_data")

    mock_upload_response = MagicMock()
    mock_upload_response.ok = True
    responses = [
        {"media_id_string": f"id_{i}"}
        for i in range(4)
    ]
    mock_upload_response.json = AsyncMock(side_effect=responses)

    mock_session = AsyncMock()
    mock_session.get.return_value.__aenter__.return_value = mock_media_response
    mock_session.post.return_value.__aenter__.return_value = mock_upload_response

    with patch.object(twitter_api, "session", mock_session):
        media_ids = await twitter_api._upload_media([
            f"https://example.com/image{i}.jpg"
            for i in range(4)
        ])

        assert len(media_ids) == 4
        assert all(f"id_{i}" in media_ids for i in range(4))
@pytest.mark.asyncio
async def test_media_validation():
    """Test media validation rules."""
    twitter_api = TwitterAPI(auth_token="test_token")

    # Test too many media attachments
    post = SocialPost(
        content="Test post",
        media_urls=[
            f"https://example.com/image{i}.jpg"
            for i in range(5)  # Twitter limit is 4
        ]
    )

    with pytest.raises(PlatformError, match="Maximum 4 media items allowed"):
        await twitter_api.post(post)

    # Test invalid media URLs
    invalid_urls = [
        "not-a-url",
        "ftp://example.com/image.jpg",
        "file:///local/image.jpg"
    ]

    for url in invalid_urls:
        post = SocialPost(
            content="Test post",
            media_urls=[url]
        )
        with pytest.raises(PlatformError, match="Invalid media URL"):
            await twitter_api.post(post)

    # Test unsupported media types
    unsupported_types = [
        "https://example.com/file.exe",
        "https://example.com/doc.pdf",
        "https://example.com/audio.mp3"
    ]

    for url in unsupported_types:
        post = SocialPost(
            content="Test post",
            media_urls=[url]
        )
        with pytest.raises(PlatformError, match="Unsupported media type"):
            await twitter_api.post(post)
