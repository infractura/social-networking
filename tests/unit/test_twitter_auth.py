import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timedelta

from social_integrator.auth.providers.twitter import TwitterAuthProvider
from social_integrator.auth.auth_manager import TokenInfo

@pytest.fixture
def twitter_auth():
    """Create a TwitterAuthProvider instance."""
    return TwitterAuthProvider(
        client_id="test_client_id",
        client_secret="test_client_secret",
        redirect_uri="http://localhost:8080/callback"
    )

@pytest.mark.asyncio
async def test_twitter_auth_initialization(twitter_auth):
    """Test TwitterAuthProvider initialization."""
    assert twitter_auth.client_id == "test_client_id"
    assert twitter_auth.client_secret == "test_client_secret"
    assert twitter_auth.redirect_uri == "http://localhost:8080/callback"
    assert "tweet.read" in twitter_auth.scopes
    assert "tweet.write" in twitter_auth.scopes

@pytest.mark.asyncio
async def test_twitter_auth_flow(twitter_auth):
    """Test OAuth flow."""
    # Mock the local server
    mock_queue = AsyncMock()
    mock_queue.get.return_value = {"code": "test_code", "state": "state"}

    # Mock token exchange response
    mock_response = MagicMock()
    mock_response.ok = True
    mock_response.json.return_value = {
        "access_token": "test_access_token",
        "token_type": "Bearer",
        "expires_in": 7200,
        "refresh_token": "test_refresh_token",
        "scope": "tweet.read tweet.write"
    }

    # Mock aiohttp session
    mock_session = AsyncMock()
    mock_session.post.return_value.__aenter__.return_value = mock_response

    with patch("aiohttp.ClientSession", return_value=mock_session), \
         patch("webbrowser.open"), \
         patch.object(twitter_auth, "_start_local_server", return_value=mock_queue):

        token_info = await twitter_auth.authenticate()

        assert isinstance(token_info, TokenInfo)
        assert token_info.access_token == "test_access_token"
        assert token_info.refresh_token == "test_refresh_token"
        assert token_info.platform == "twitter"

@pytest.mark.asyncio
async def test_twitter_token_refresh(twitter_auth):
    """Test token refresh."""
    # Create expired token
    expired_token = TokenInfo(
        access_token="old_token",
        refresh_token="refresh_token",
        expires_at=datetime.utcnow() - timedelta(hours=1),
        platform="twitter"
    )

    # Mock refresh response
    mock_response = MagicMock()
    mock_response.ok = True
    mock_response.json.return_value = {
        "access_token": "new_token",
        "token_type": "Bearer",
        "expires_in": 7200,
        "refresh_token": "new_refresh_token"
    }

    # Mock aiohttp session
    mock_session = AsyncMock()
    mock_session.post.return_value.__aenter__.return_value = mock_response

    with patch("aiohttp.ClientSession", return_value=mock_session):
        new_token = await twitter_auth.refresh(expired_token)

        assert isinstance(new_token, TokenInfo)
        assert new_token.access_token == "new_token"
        assert new_token.refresh_token == "new_refresh_token"

@pytest.mark.asyncio
async def test_twitter_auth_errors(twitter_auth):
    """Test error handling in authentication."""
    # Mock error response
    mock_response = MagicMock()
    mock_response.ok = False
    mock_response.text.return_value = "Authentication failed"

    # Mock aiohttp session
    mock_session = AsyncMock()
    mock_session.post.return_value.__aenter__.return_value = mock_response

    with patch("aiohttp.ClientSession", return_value=mock_session), \
         patch("webbrowser.open"), \
         pytest.raises(ValueError, match="Token exchange failed"):

        await twitter_auth.authenticate()
