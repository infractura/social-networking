import asyncio
from datetime import datetime, UTC
from typing import Dict, Optional
import json
import os
from pathlib import Path
from pydantic import BaseModel, ConfigDict

class TokenInfo(BaseModel):
    """Token information."""
    access_token: str
    token_type: str = "Bearer"
    expires_at: Optional[datetime] = None
    refresh_token: Optional[str] = None
    platform: str

    model_config = ConfigDict(frozen=True)

    @property
    def is_expired(self) -> bool:
        """Check if token is expired."""
        if not self.expires_at:
            return False
        # Convert naive datetime to UTC if needed
        expires_at = self.expires_at.replace(tzinfo=UTC) if self.expires_at.tzinfo is None else self.expires_at
        return datetime.now(UTC) > expires_at

class TokenStore:
    """Store for authentication tokens."""
    
    def __init__(self, storage_path: str):
        """Initialize token store.
        
        Args:
            storage_path: Path to token storage file
        """
        self.storage_path = str(Path(storage_path).resolve())
        self._tokens: Dict[str, TokenInfo] = {}
        self._load_tokens()
    
    def _load_tokens(self) -> None:
        """Load tokens from storage."""
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(self.storage_path), exist_ok=True)

        if not os.path.exists(self.storage_path):
            try:
                # Create empty token file
                with open(self.storage_path, 'w') as f:
                    json.dump({}, f)
            except OSError as e:
                raise RuntimeError(f"Failed to create token file: {e}")
            return

        try:
            with open(self.storage_path, 'r') as f:
                data = json.load(f)
                for platform, token_data in data.items():
                    # Convert expires_at string to datetime
                    if token_data.get('expires_at'):
                        token_data['expires_at'] = datetime.fromisoformat(token_data['expires_at'])
                    self._tokens[platform] = TokenInfo(**token_data)
        except (json.JSONDecodeError, OSError) as e:
            raise RuntimeError(f"Failed to load tokens: {e}")
    
    def _save_tokens(self) -> None:
        """Save tokens to storage."""
        try:
            data = {}
            for platform, token in self._tokens.items():
                token_dict = token.model_dump()
                # Convert datetime to ISO format string
                if token_dict.get('expires_at'):
                    token_dict['expires_at'] = token_dict['expires_at'].isoformat()
                data[platform] = token_dict
            
            with open(self.storage_path, 'w') as f:
                json.dump(data, f)
        except OSError as e:
            raise RuntimeError(f"Failed to save tokens: {e}")
    
    def store_token(self, token: TokenInfo) -> None:
        """Store a token.
        
        Args:
            token: Token to store
        """
        self._tokens[token.platform] = token
        self._save_tokens()
    
    def get_token(self, platform: str) -> Optional[TokenInfo]:
        """Get token for platform.
        
        Args:
            platform: Platform identifier
            
        Returns:
            Token if found, None otherwise
        """
        return self._tokens.get(platform)
    
    def remove_token(self, platform: str) -> None:
        """Remove token for platform.
        
        Args:
            platform: Platform identifier
        """
        if platform in self._tokens:
            del self._tokens[platform]
            self._save_tokens()

class AuthProvider:
    """Base class for authentication providers."""
    
    async def authenticate(self) -> TokenInfo:
        """Authenticate and get token.
        
        Returns:
            Authentication token
        """
        raise NotImplementedError
    
    async def refresh(self, token_info: TokenInfo) -> TokenInfo:
        """Refresh authentication token.
        
        Args:
            token_info: Current token information
            
        Returns:
            New token information
        """
        raise NotImplementedError

class AuthManager:
    """Manages authentication for social media platforms."""
    
    def __init__(self, token_store: Optional[TokenStore] = None):
        """Initialize auth manager.
        
        Args:
            token_store: Optional token store instance
        """
        self.token_store = token_store or TokenStore(".tokens.json")
        self._providers: Dict[str, AuthProvider] = {}
        self._auth_locks: Dict[str, asyncio.Lock] = {}
    
    def register_provider(self, platform: str, provider: AuthProvider) -> None:
        """Register authentication provider.
        
        Args:
            platform: Platform identifier
            provider: Authentication provider
        """
        self._providers[platform] = provider
        self._auth_locks[platform] = asyncio.Lock()
    
    async def get_valid_token(self, platform: str) -> TokenInfo:
        """Get valid token for platform.
        
        Args:
            platform: Platform identifier
            
        Returns:
            Valid token
            
        Raises:
            KeyError: If no provider registered for platform
            ValueError: If authentication fails
        """
        if platform not in self._providers:
            raise KeyError(f"No provider registered for platform: {platform}")
        
        async with self._auth_locks[platform]:
            # Check for existing valid token
            token = self.token_store.get_token(platform)
            if token and not token.is_expired:
                return token
            
            # Try to refresh if we have a refresh token
            if token and token.refresh_token:
                try:
                    new_token = await self._providers[platform].refresh(token)
                    self.token_store.store_token(new_token)
                    return new_token
                except Exception as e:
                    # If refresh fails, remove the token and re-raise the error
                    self.token_store.remove_token(platform)
                    raise
            
            # Full authentication if no token or refresh failed
            token = await self._providers[platform].authenticate()
            self.token_store.store_token(token)
            return token
    
    def revoke_token(self, platform: str) -> None:
        """Revoke token for platform.
        
        Args:
            platform: Platform identifier
        """
        self.token_store.remove_token(platform)
