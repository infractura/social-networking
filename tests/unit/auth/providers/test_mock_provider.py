import pytest
from datetime import datetime, timedelta, UTC
from social_integrator.auth.auth_manager import TokenInfo

@pytest.mark.asyncio
async def test_mock_provider_authentication(mock_provider):
    """Test basic authentication with MockAuthProvider."""
    token = await mock_provider.authenticate()
    
    assert token.access_token == "mock_token_1"
    assert token.token_type == "Bearer"
    assert token.refresh_token == "mock_refresh_token"
    assert token.platform == "mock"
    assert not token.is_expired
    assert mock_provider.auth_count == 1

@pytest.mark.asyncio
async def test_mock_provider_refresh(mock_provider):
    """Test token refresh with MockAuthProvider."""
    # Create expired token
    expired_token = TokenInfo(
        access_token="old_token",
        platform="mock",
        expires_at=datetime.now(UTC) - timedelta(hours=1),
        refresh_token="mock_refresh_token"
    )
    
    # Refresh the token
    new_token = await mock_provider.refresh(expired_token)
    
    assert new_token.access_token == "mock_refreshed_token_1"
    assert new_token.refresh_token == "mock_refresh_token"
    assert not new_token.is_expired
    assert mock_provider.refresh_count == 1

@pytest.mark.asyncio
async def test_mock_provider_authentication_failure(failing_mock_provider):
    """Test authentication failure handling."""
    with pytest.raises(ValueError, match="Authentication failed"):
        await failing_mock_provider.authenticate()

@pytest.mark.asyncio
async def test_mock_provider_refresh_failure(failing_mock_provider):
    """Test refresh failure handling."""
    token = TokenInfo(
        access_token="old_token",
        platform="mock",
        refresh_token="mock_refresh_token"
    )
    
    with pytest.raises(ValueError, match="Refresh failed"):
        await failing_mock_provider.refresh(token)

@pytest.mark.asyncio
async def test_mock_provider_token_lifetime(mock_provider):
    """Test token lifetime configuration."""
    # Configure provider with short lifetime
    mock_provider.token_lifetime = 60  # 1 minute
    
    # Get token
    token = await mock_provider.authenticate()
    
    # Verify expiration time
    assert token.expires_at is not None
    time_diff = token.expires_at - datetime.now(UTC)
    assert 55 <= time_diff.total_seconds() <= 65  # Allow small timing variations

@pytest.mark.asyncio
async def test_mock_provider_multiple_authentications(mock_provider):
    """Test multiple authentication attempts."""
    tokens = []
    for _ in range(3):
        token = await mock_provider.authenticate()
        tokens.append(token)
    
    # Verify increasing token numbers
    assert tokens[0].access_token == "mock_token_1"
    assert tokens[1].access_token == "mock_token_2"
    assert tokens[2].access_token == "mock_token_3"
    assert mock_provider.auth_count == 3

@pytest.mark.asyncio
async def test_mock_provider_multiple_refreshes(mock_provider):
    """Test multiple refresh attempts."""
    token = TokenInfo(
        access_token="old_token",
        platform="mock",
        refresh_token="mock_refresh_token"
    )
    
    refreshed_tokens = []
    for _ in range(3):
        new_token = await mock_provider.refresh(token)
        refreshed_tokens.append(new_token)
    
    # Verify increasing refresh numbers
    assert refreshed_tokens[0].access_token == "mock_refreshed_token_1"
    assert refreshed_tokens[1].access_token == "mock_refreshed_token_2"
    assert refreshed_tokens[2].access_token == "mock_refreshed_token_3"
    assert mock_provider.refresh_count == 3
