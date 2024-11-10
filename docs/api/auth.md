# Authentication API Reference

Reference documentation for authentication components.

## TokenInfo

```python
class TokenInfo(BaseModel):
    """Model for storing token information."""

    access_token: str
    token_type: str = "Bearer"
    expires_at: Optional[datetime] = None
    refresh_token: Optional[str] = None
    scope: Optional[str] = None
    platform: str

    @property
    def is_expired(self) -> bool:
        """Check if the token is expired."""
```

## AuthProvider

```python
class AuthProvider(ABC):
    """Abstract base class for authentication providers."""

    @abstractmethod
    async def authenticate(self) -> TokenInfo:
        """Authenticate and get token info."""

    @abstractmethod
    async def refresh(self, token_info: TokenInfo) -> TokenInfo:
        """Refresh an expired token."""
```

## TokenStore

```python
class TokenStore:
    """Manages storage and retrieval of authentication tokens."""

    def __init__(self, storage_path: Optional[str] = None):
        """Initialize token store.

        Args:
            storage_path: Path to token storage file.
                         Defaults to ~/.social_integrator/tokens.json
        """

    def get_token(self, platform: str) -> Optional[TokenInfo]:
        """Get token info for a platform."""

    def store_token(self, token_info: TokenInfo) -> None:
        """Store token info for a platform."""

    def remove_token(self, platform: str) -> None:
        """Remove token for a platform."""
```

## AuthManager

```python
class AuthManager:
    """Manages authentication across different platforms."""

    def register_provider(self, platform: str, provider: AuthProvider) -> None:
        """Register an authentication provider for a platform."""

    async def get_valid_token(self, platform: str) -> TokenInfo:
        """Get a valid token for a platform, refreshing if necessary."""

    def revoke_token(self, platform: str) -> None:
        """Revoke token for a platform."""
```

## Twitter Authentication

```python
class TwitterAuthProvider(AuthProvider):
    """Twitter OAuth 2.0 authentication provider."""

    def __init__(
        self,
        client_id: str,
        client_secret: str,
        redirect_uri: str,
        scopes: Optional[list[str]] = None
    ):
        """Initialize Twitter auth provider.

        Args:
            client_id: Twitter API client ID
            client_secret: Twitter API client secret
            redirect_uri: OAuth redirect URI
            scopes: List of requested scopes
        """
```
