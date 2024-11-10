import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import aiohttp
from social_integrator.core.platform import PlatformError, RateLimitError

@pytest.mark.asyncio
async def test_retry_on_rate_limit(twitter_api, social_post):
    """Test retry behavior on rate limit errors."""
    # Mock responses: first rate limit, then success
    responses = [
        MagicMock(status=429, headers={"Retry-After": "1"}),
        MagicMock(
            status=200,
            ok=True,
            json=AsyncMock(return_value={"data": {"id": "123"}})
        )
    ]

    mock_session = AsyncMock()
    mock_session.post.side_effect = [
        AsyncMock(__aenter__=AsyncMock(return_value=resp))
        for resp in responses
    ]

    with patch.object(twitter_api, "session", mock_session):
        result = await twitter_api.post(social_post)
        assert result["data"]["id"] == "123"
        assert mock_session.post.call_count == 2

@pytest.mark.asyncio
async def test_retry_on_network_error(twitter_api, social_post):
    """Test retry behavior on network errors."""
    # Mock responses: first network error, then success
    mock_session = AsyncMock()
    mock_session.post.side_effect = [
        aiohttp.ClientError("Network error"),
        AsyncMock(
            __aenter__=AsyncMock(
                return_value=MagicMock(
                    ok=True,
                    json=AsyncMock(return_value={"data": {"id": "123"}})
                )
            )
        )
    ]

    with patch.object(twitter_api, "session", mock_session):
        result = await twitter_api.post(social_post)
        assert result["data"]["id"] == "123"
        assert mock_session.post.call_count == 2

@pytest.mark.asyncio
async def test_retry_exhaustion(twitter_api, social_post):
    """Test behavior when retries are exhausted."""
    # Mock continuous rate limit responses
    mock_response = MagicMock(status=429, headers={"Retry-After": "1"})
    mock_session = AsyncMock()
    mock_session.post.return_value.__aenter__.return_value = mock_response

    with patch.object(twitter_api, "session", mock_session):
        with pytest.raises(RateLimitError):
            await twitter_api.post(social_post)

        # Should have tried the maximum number of times
        assert mock_session.post.call_count == twitter_api.config.max_retries

@pytest.mark.asyncio
async def test_no_retry_on_validation_error(twitter_api, social_post):
    """Test that validation errors are not retried."""
    # Mock validation error response
    mock_response = MagicMock(
        status=400,
        json=AsyncMock(return_value={
            "errors": [{"message": "Invalid request"}]
        })
    )

    mock_session = AsyncMock()
    mock_session.post.return_value.__aenter__.return_value = mock_response

    with patch.object(twitter_api, "session", mock_session):
        with pytest.raises(PlatformError, match="Invalid request"):
            await twitter_api.post(social_post)

        # Should not have retried
        assert mock_session.post.call_count == 1

@pytest.mark.asyncio
async def test_retry_with_server_errors(twitter_api, social_post):
    """Test retry behavior with server errors (5xx)."""
    # Mock responses: 503, 502, success
    responses = [
        MagicMock(status=503, ok=False),
        MagicMock(status=502, ok=False),
        MagicMock(
            status=200,
            ok=True,
            json=AsyncMock(return_value={"data": {"id": "123"}})
        )
    ]

    mock_session = AsyncMock()
    mock_session.post.side_effect = [
        AsyncMock(__aenter__=AsyncMock(return_value=resp))
        for resp in responses
    ]

    with patch.object(twitter_api, "session", mock_session):
        result = await twitter_api.post(social_post)
        assert result["data"]["id"] == "123"
        assert mock_session.post.call_count == 3
