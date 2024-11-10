import os
from datetime import datetime, timedelta
import pytest

from social_integrator.auth.auth_manager import TokenInfo, TokenStore, AuthManager, AuthProvider

class MockAuthProvider(AuthProvider):
    """Mock auth provider for testing."""
    def __init__(self, should_fail=False):
        self.should_fail = should_fail
        self.auth_count = 0
        self.refresh_count = 0

    async def authenticate(self) -> TokenInfo:
        if self.should_fail:
            raise ValueError("Authentication failed")
        self.auth_count += 1
        return TokenInfo(
            access_token=f"mock_token_{self.auth_count}",
            expires_at=datetime.utcnow() + timedelta(hours=1),
            refresh_token="mock_refresh",
            platform="mock"
        )

    async def refresh(self, token_info: TokenInfo) -> TokenInfo:
        if self.should_fail:
            raise ValueError("Refresh failed")
        self.refresh_count += 1
        return TokenInfo(
            access_token=f"refreshed_token_{self.refresh_count}",
            expires_at=datetime.utcnow() + timedelta(hours=1),
            refresh_token=token_info.refresh_token,
            platform="mock"
        )

@pytest.fixture
def temp_token_file(tmp_path):
    """Create a temporary token file."""
    return str(tmp_path / "tokens.json")

@pytest.mark.asyncio
async def test_token_store_operations(temp_token_file):
    """Test basic TokenStore operations."""
    store = TokenStore(temp_token_file)

    # Store token
    token = TokenInfo(
        access_token="test_token",
        platform="test"
    )
    store.store_token(token)

    # Get token
    retrieved = store.get_token("test")
    assert retrieved is not None
    assert retrieved.access_token == "test_token"

    # Remove token
    store.remove_token("test")
    assert store.get_token("test") is None

@pytest.mark.asyncio
async def test_auth_manager_token_lifecycle(temp_token_file):
    """Test AuthManager token lifecycle."""
    manager = AuthManager()
    provider = MockAuthProvider()
    manager.register_provider("mock", provider)

    # Get new token
    token = await manager.get_valid_token("mock")
    assert token.access_token == "mock_token_1"
    assert provider.auth_count == 1

    # Get cached token
    token = await manager.get_valid_token("mock")
    assert token.access_token == "mock_token_1"
    assert provider.auth_count == 1  # Should not have changed

@pytest.mark.asyncio
async def test_auth_manager_token_refresh(temp_token_file):
    """Test token refresh behavior."""
    manager = AuthManager()
    provider = MockAuthProvider()
    manager.register_provider("mock", provider)

    # Store expired token
    expired_token = TokenInfo(
        access_token="expired",
        platform="mock",
        expires_at=datetime.utcnow() - timedelta(hours=1),
        refresh_token="mock_refresh"
    )
    manager.token_store.store_token(expired_token)

    # Get token (should refresh)
    token = await manager.get_valid_token("mock")
    assert token.access_token == "refreshed_token_1"
    assert provider.refresh_count == 1

@pytest.mark.asyncio
async def test_auth_manager_error_handling(temp_token_file):
    """Test error handling in AuthManager."""
    manager = AuthManager()
    provider = MockAuthProvider(should_fail=True)
    manager.register_provider("mock", provider)

    # Test authentication failure
    with pytest.raises(ValueError, match="Authentication failed"):
        await manager.get_valid_token("mock")

    # Test refresh failure
    expired_token = TokenInfo(
        access_token="expired",
        platform="mock",
        expires_at=datetime.utcnow() - timedelta(hours=1),
        refresh_token="mock_refresh"
    )
    manager.token_store.store_token(expired_token)

    with pytest.raises(ValueError, match="Refresh failed"):
        await manager.get_valid_token("mock")
