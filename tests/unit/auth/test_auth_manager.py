import pytest
import asyncio
from datetime import datetime, timedelta, UTC
from social_integrator.auth.auth_manager import AuthManager, TokenInfo, TokenStore
from .conftest import MockAuthProvider

@pytest.mark.asyncio
async def test_auth_manager_basic(mock_provider, tmp_path):
    """Test basic AuthManager functionality."""
    token_file = tmp_path / "tokens.json"
    manager = AuthManager(TokenStore(str(token_file)))
    
    # Register provider
    manager.register_provider("mock", mock_provider)
    
    # Get token (should authenticate)
    token = await manager.get_valid_token("mock")
    assert token.access_token == "mock_token_1"
    assert mock_provider.auth_count == 1
    
    # Get token again (should use cached)
    token = await manager.get_valid_token("mock")
    assert token.access_token == "mock_token_1"
    assert mock_provider.auth_count == 1  # Should not have changed

@pytest.mark.asyncio
async def test_auth_manager_token_refresh(mock_provider, tmp_path):
    """Test token refresh functionality."""
    token_file = tmp_path / "tokens.json"
    manager = AuthManager(TokenStore(str(token_file)))
    manager.register_provider("mock", mock_provider)
    
    # Store expired token
    manager.token_store.store_token(TokenInfo(
        access_token="expired_token",
        platform="mock",
        expires_at=datetime.now(UTC) - timedelta(hours=1),
        refresh_token="mock_refresh_token"
    ))
    
    # Should refresh the token
    token = await manager.get_valid_token("mock")
    assert token.access_token.startswith("mock_refreshed_token")
    assert mock_provider.refresh_count == 1

@pytest.mark.asyncio
async def test_auth_manager_token_revocation(mock_provider, tmp_path):
    """Test token revocation."""
    token_file = tmp_path / "tokens.json"
    manager = AuthManager(TokenStore(str(token_file)))
    manager.register_provider("mock", mock_provider)
    
    # Get initial token
    token1 = await manager.get_valid_token("mock")
    
    # Revoke and get new token
    manager.revoke_token("mock")
    token2 = await manager.get_valid_token("mock")
    
    assert token1.access_token != token2.access_token
    assert mock_provider.auth_count == 2  # Should authenticate twice

@pytest.mark.asyncio
async def test_auth_manager_errors(failing_mock_provider, tmp_path):
    """Test authentication error handling."""
    token_file = tmp_path / "tokens.json"
    manager = AuthManager(TokenStore(str(token_file)))
    manager.register_provider("mock", failing_mock_provider)
    
    # Test authentication failure
    with pytest.raises(ValueError, match="Authentication failed"):
        await manager.get_valid_token("mock")
    
    # Test refresh failure
    manager.token_store.store_token(TokenInfo(
        access_token="expired_token",
        platform="mock",
        expires_at=datetime.now(UTC) - timedelta(hours=1),
        refresh_token="mock_refresh_token"
    ))
    
    with pytest.raises(ValueError, match="Refresh failed"):
        await manager.get_valid_token("mock")

@pytest.mark.asyncio
async def test_auth_manager_concurrent_requests(mock_provider, tmp_path):
    """Test concurrent authentication requests."""
    token_file = tmp_path / "tokens.json"
    manager = AuthManager(TokenStore(str(token_file)))
    manager.register_provider("mock", mock_provider)
    
    # Make concurrent requests
    tasks = [manager.get_valid_token("mock") for _ in range(5)]
    tokens = await asyncio.gather(*tasks)
    
    # Should only authenticate once
    assert mock_provider.auth_count == 1
    assert all(token.access_token == "mock_token_1" for token in tokens)

@pytest.mark.asyncio
async def test_auth_manager_refresh_race_condition(mock_provider, tmp_path):
    """Test handling of concurrent refresh requests."""
    token_file = tmp_path / "tokens.json"
    manager = AuthManager(TokenStore(str(token_file)))
    manager.register_provider("mock", mock_provider)
    
    # Store expired token
    manager.token_store.store_token(TokenInfo(
        access_token="expired_token",
        platform="mock",
        expires_at=datetime.now(UTC) - timedelta(hours=1),
        refresh_token="mock_refresh_token"
    ))
    
    # Make concurrent refresh requests
    tasks = [manager.get_valid_token("mock") for _ in range(5)]
    tokens = await asyncio.gather(*tasks)
    
    # Should only refresh once
    assert mock_provider.refresh_count == 1
    assert all(token.access_token == "mock_refreshed_token_1" for token in tokens)

@pytest.mark.asyncio
async def test_auth_manager_multiple_providers(mock_provider, tmp_path):
    """Test AuthManager with multiple providers."""
    token_file = tmp_path / "tokens.json"
    manager = AuthManager(TokenStore(str(token_file)))
    
    # Register multiple providers
    providers = {
        "mock1": MockAuthProvider(platform="mock1"),
        "mock2": MockAuthProvider(platform="mock2"),
        "mock3": MockAuthProvider(platform="mock3")
    }
    
    for platform, provider in providers.items():
        manager.register_provider(platform, provider)
    
    # Get tokens for each provider
    tokens = {}
    for platform in providers:
        tokens[platform] = await manager.get_valid_token(platform)
    
    # Verify each provider was used
    for platform, provider in providers.items():
        assert provider.auth_count == 1
        assert tokens[platform].platform == platform

@pytest.mark.asyncio
async def test_auth_manager_provider_not_found(tmp_path):
    """Test handling of non-existent provider."""
    token_file = tmp_path / "tokens.json"
    manager = AuthManager(TokenStore(str(token_file)))
    
    with pytest.raises(KeyError, match="No provider registered for platform"):
        await manager.get_valid_token("nonexistent")
