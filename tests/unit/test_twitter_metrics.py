import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import aiohttp
import asyncio

from social_integrator.platforms.twitter import TwitterAPI
from social_integrator.core.platform import PlatformError

@pytest.fixture
def twitter_api():
    """Create a TwitterAPI instance."""
    return TwitterAPI(auth_token="test_token")

@pytest.mark.asyncio
async def test_get_metrics(twitter_api):
    """Test getting post metrics."""
    # Mock successful metrics response
    mock_response = MagicMock()
    mock_response.ok = True
    mock_response.json = AsyncMock(return_value={
        "data": {
            "public_metrics": {
                "retweet_count": 10,
                "reply_count": 5,
                "like_count": 20,
                "quote_count": 3
            }
        }
    })

    mock_session = AsyncMock()
    mock_session.get.return_value.__aenter__.return_value = mock_response

    with patch.object(twitter_api, "session", mock_session):
        metrics = await twitter_api.get_metrics("123456789")

        assert metrics["retweet_count"] == 10
        assert metrics["reply_count"] == 5
        assert metrics["like_count"] == 20
        assert metrics["quote_count"] == 3

@pytest.mark.asyncio
async def test_get_metrics_not_found(twitter_api):
    """Test getting metrics for non-existent post."""
    # Mock 404 response
    mock_response = MagicMock()
    mock_response.status = 404
    mock_response.json = AsyncMock(return_value={
        "errors": [{"message": "Tweet not found"}]
    })

    mock_session = AsyncMock()
    mock_session.get.return_value.__aenter__.return_value = mock_response

    with patch.object(twitter_api, "session", mock_session):
        with pytest.raises(PlatformError, match="Tweet not found"):
            await twitter_api.get_metrics("nonexistent")

@pytest.mark.asyncio
async def test_get_metrics_rate_limit(twitter_api):
    """Test rate limit handling for metrics."""
    # Mock rate limit response
    mock_response = MagicMock()
    mock_response.status = 429
    mock_response.headers = {"Retry-After": "60"}

    mock_session = AsyncMock()
    mock_session.get.return_value.__aenter__.return_value = mock_response

    with patch.object(twitter_api, "session", mock_session):
        with pytest.raises(PlatformError, match="Rate limit exceeded"):
            await twitter_api.get_metrics("123456789")

@pytest.mark.asyncio
async def test_get_metrics_batch(twitter_api):
    """Test getting metrics for multiple posts."""
    # Mock successful batch metrics response
    mock_response = MagicMock()
    mock_response.ok = True
    mock_response.json = AsyncMock(return_value={
        "data": [
            {
                "id": f"tweet_{i}",
                "public_metrics": {
                    "retweet_count": i,
                    "like_count": i * 2
                }
            }
            for i in range(3)
        ]
    })

    mock_session = AsyncMock()
    mock_session.get.return_value.__aenter__.return_value = mock_response

    with patch.object(twitter_api, "session", mock_session):
        tweet_ids = [f"tweet_{i}" for i in range(3)]
        metrics = await twitter_api.get_metrics_batch(tweet_ids)

        assert len(metrics) == 3
        for i, metric in enumerate(metrics):
            assert metric["retweet_count"] == i
            assert metric["like_count"] == i * 2
@pytest.mark.asyncio
async def test_metrics_caching(twitter_api):
    """Test metrics caching functionality."""
    # Mock successful metrics response
    mock_response = MagicMock()
    mock_response.ok = True
    mock_response.json = AsyncMock(return_value={
        "data": {
            "public_metrics": {
                "retweet_count": 10,
                "like_count": 20
            }
        }
    })

    mock_session = AsyncMock()
    mock_session.get.return_value.__aenter__.return_value = mock_response

    with patch.object(twitter_api, "session", mock_session):
        # First call should hit the API
        metrics1 = await twitter_api.get_metrics("123456789")
        assert mock_session.get.call_count == 1

        # Second call within cache time should use cached value
        metrics2 = await twitter_api.get_metrics("123456789")
        assert mock_session.get.call_count == 1  # No additional API call
        assert metrics1 == metrics2  # Same data returned

        # Wait for cache to expire
        await asyncio.sleep(twitter_api.config.metrics_cache_ttl + 0.1)

        # Call after cache expiry should hit API again
        metrics3 = await twitter_api.get_metrics("123456789")
        assert mock_session.get.call_count == 2

@pytest.mark.asyncio
async def test_metrics_cache_invalidation(twitter_api):
    """Test metrics cache invalidation."""
    # Mock responses
    responses = [
        {
            "data": {
                "public_metrics": {
                    "retweet_count": i * 10,
                    "like_count": i * 20
                }
            }
        }
        for i in range(1, 3)
    ]

    mock_response = MagicMock()
    mock_response.ok = True
    mock_response.json = AsyncMock(side_effect=responses)

    mock_session = AsyncMock()
    mock_session.get.return_value.__aenter__.return_value = mock_response

    with patch.object(twitter_api, "session", mock_session):
        # Get initial metrics
        metrics1 = await twitter_api.get_metrics("123456789")
        assert metrics1["retweet_count"] == 10

        # Invalidate cache
        twitter_api.invalidate_metrics_cache("123456789")

        # Get metrics again (should hit API with new data)
        metrics2 = await twitter_api.get_metrics("123456789")
        assert metrics2["retweet_count"] == 20
        assert mock_session.get.call_count == 2
