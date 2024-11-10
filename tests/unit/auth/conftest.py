import pytest
from datetime import datetime, timedelta, UTC
from typing import Optional
from social_integrator.auth.auth_manager import TokenInfo, AuthProvider

class MockAuthProvider(AuthProvider):
    """Mock authentication provider for testing."""
    
    def __init__(
        self,
        should_fail: bool = False,
        token_lifetime: int = 3600,
        platform: str = "mock"
    ):
        self.should_fail = should_fail
        self.token_lifetime = token_lifetime
        self.platform = platform
        self.auth_count = 0
        self.refresh_count = 0
    
    async def authenticate(self) -> TokenInfo:
        """Mock authentication."""
        if self.should_fail:
            raise ValueError("Authentication failed")
        
        self.auth_count += 1
        return TokenInfo(
            access_token=f"{self.platform}_token_{self.auth_count}",
            token_type="Bearer",
            expires_at=datetime.now(UTC) + timedelta(seconds=self.token_lifetime),
            refresh_token=f"{self.platform}_refresh_token",
            platform=self.platform
        )
    
    async def refresh(self, token_info: TokenInfo) -> TokenInfo:
        """Mock token refresh."""
        if self.should_fail:
            raise ValueError("Refresh failed")
        
        self.refresh_count += 1
        return TokenInfo(
            access_token=f"{self.platform}_refreshed_token_{self.refresh_count}",
            token_type="Bearer",
            expires_at=datetime.now(UTC) + timedelta(seconds=self.token_lifetime),
            refresh_token=token_info.refresh_token,
            platform=self.platform
        )

@pytest.fixture
def mock_provider():
    """Create a mock auth provider."""
    return MockAuthProvider()

@pytest.fixture
def failing_mock_provider():
    """Create a mock auth provider that fails."""
    return MockAuthProvider(should_fail=True)

@pytest.fixture
def temp_token_file(tmp_path):
    """Create a temporary token file."""
    token_file = tmp_path / "tokens.json"
    return str(token_file)
