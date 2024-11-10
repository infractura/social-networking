import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import asyncio
import aiohttp

from social_integrator.platforms.twitter import TwitterAPI
from social_integrator.core.platform import PlatformError, RateLimitError

@pytest.fixture
def twitter_api():
    """Create a TwitterAPI instance."""
    return TwitterAPI(auth_token="test_token")

@pytest.mark.asyncio
async def test_handle_rate_limit_response(twitter_api):
    """Test handling of rate limit responses."""
    # Create mock response with rate limit headers
    mock_response = MagicMock()
    mock_response.status = 429
    mock_response.headers = {"Retry-After": "60"}

    with pytest.raises(RateLimitError) as exc:
        await twitter_api._handle_response(mock_response)

    assert "60" in str(exc.value)  # Should include retry delay

@pytest.mark.asyncio
async def test_handle_error_response(twitter_api):
    """Test handling of error responses."""
    # Create mock error response
    mock_response = MagicMock()
    mock_response.status = 400
    mock_response.json = AsyncMock(return_value={
        "errors": [{"message": "Invalid request"}]
    })

    with pytest.raises(PlatformError, match="Invalid request"):
        await twitter_api._handle_response(mock_response)

@pytest.mark.asyncio
async def test_handle_invalid_json_response(twitter_api):
    """Test handling of invalid JSON responses."""
    # Create mock response with invalid JSON
    mock_response = MagicMock()
    mock_response.json = AsyncMock(side_effect=aiohttp.ContentTypeError(
        None, None
    ))
    mock_response.text = AsyncMock(return_value="Invalid JSON")

    with pytest.raises(PlatformError, match="Invalid response"):
        await twitter_api._handle_response(mock_response)

@pytest.mark.asyncio
async def test_handle_success_response(twitter_api):
    """Test handling of successful responses."""
    # Create mock success response
    mock_response = MagicMock()
    mock_response.ok = True
    mock_response.json = AsyncMock(return_value={
        "data": {"id": "123"}
    })

    result = await twitter_api._handle_response(mock_response)
    assert result["data"]["id"] == "123"

@pytest.mark.asyncio
async def test_handle_network_errors():
    """Test handling of network-related errors."""
    # Mock session that raises network error
    mock_session = AsyncMock()
    mock_session.post.side_effect = aiohttp.ClientError("Network error")

    with patch("aiohttp.ClientSession", return_value=mock_session):
        api = TwitterAPI(auth_token="test_token")
        with pytest.raises(PlatformError, match="Network error"):
            await api.post({"content": "test"})

@pytest.mark.asyncio
async def test_handle_timeout():
    """Test handling of timeout errors."""
    # Mock session that raises timeout
    mock_session = AsyncMock()
    mock_session.post.side_effect = asyncio.TimeoutError()

    with patch("aiohttp.ClientSession", return_value=mock_session):
        api = TwitterAPI(auth_token="test_token")
        with pytest.raises(PlatformError, match="Request timed out"):
            await api.post({"content": "test"})
@pytest.mark.asyncio
async def test_session_lifecycle():
    """Test proper session creation and cleanup."""
    mock_session = AsyncMock()

    with patch("aiohttp.ClientSession", return_value=mock_session):
        api = TwitterAPI(auth_token="test_token")
        
        # Test context manager
        async with api:
            # Session should be created
            assert hasattr(api, "session")

        # Session should be closed
        mock_session.close.assert_called_once()

        # Test manual cleanup
        await api.close()
        assert mock_session.close.call_count == 2
