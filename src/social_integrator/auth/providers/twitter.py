from datetime import datetime, timedelta
import webbrowser
from typing import Optional, Dict, Any
import asyncio
import aiohttp
from urllib.parse import urlencode

from ..auth_manager import AuthProvider, TokenInfo
from ...core.config import get_platform_config


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
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri
        self.scopes = scopes or [
            "tweet.read",
            "tweet.write",
            "users.read",
            "offline.access"
        ]
        
        self.config = get_platform_config("twitter")
        if not self.config:
            raise ValueError("Twitter configuration not found")
        
        # OAuth endpoints
        self.auth_url = "https://twitter.com/i/oauth2/authorize"
        self.token_url = "https://api.twitter.com/2/oauth2/token"
    
    async def _start_local_server(self) -> asyncio.Queue:
        """Start local server to receive OAuth callback."""
        queue: asyncio.Queue = asyncio.Queue()
        
        async def handle_callback(request):
            """Handle OAuth callback."""
            params = request.query
            await queue.put(params)
            return aiohttp.web.Response(
                text="Authentication successful! You can close this window.",
                content_type="text/html"
            )
        
        app = aiohttp.web.Application()
        app.router.add_get("/callback", handle_callback)
        
        runner = aiohttp.web.AppRunner(app)
        await runner.setup()
        site = aiohttp.web.TCPSite(runner, 'localhost', 8080)
        await site.start()
        
        return queue
    
    async def _get_token_from_code(self, code: str) -> TokenInfo:
        """Exchange authorization code for tokens."""
        async with aiohttp.ClientSession() as session:
            auth = aiohttp.BasicAuth(self.client_id, self.client_secret)
            
            data = {
                "code": code,
                "grant_type": "authorization_code",
                "redirect_uri": self.redirect_uri,
                "code_verifier": "challenge"  # In production, use proper PKCE
            }
            
            async with session.post(
                self.token_url,
                data=data,
                auth=auth
            ) as response:
                if not response.ok:
                    raise ValueError(f"Token exchange failed: {await response.text()}")
                
                token_data = await response.json()
                
                return TokenInfo(
                    access_token=token_data["access_token"],
                    token_type=token_data["token_type"],
                    expires_at=datetime.utcnow() + timedelta(seconds=token_data["expires_in"]),
                    refresh_token=token_data.get("refresh_token"),
                    scope=token_data.get("scope"),
                    platform="twitter"
                )
    
    async def authenticate(self) -> TokenInfo:
        """Perform OAuth 2.0 authentication flow."""
        # Start local server for callback
        callback_queue = await self._start_local_server()
        
        # Generate authorization URL
        params = {
            "response_type": "code",
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "scope": " ".join(self.scopes),
            "state": "state",  # In production, use secure random state
            "code_challenge": "challenge",  # In production, use proper PKCE
            "code_challenge_method": "plain"
        }
        
        auth_url = f"{self.auth_url}?{urlencode(params)}"
        
        # Open browser for authentication
        print(f"Opening browser for authentication: {auth_url}")
        webbrowser.open(auth_url)
        
        # Wait for callback
        try:
            callback_params = await asyncio.wait_for(callback_queue.get(), timeout=300)
        except asyncio.TimeoutError:
            raise TimeoutError("Authentication timed out")
        
        if "error" in callback_params:
            raise ValueError(f"Authentication failed: {callback_params['error']}")
        
        code = callback_params["code"]
        return await self._get_token_from_code(code)
    
    async def refresh(self, token_info: TokenInfo) -> TokenInfo:
        """Refresh an expired token."""
        if not token_info.refresh_token:
            raise ValueError("No refresh token available")
        
        async with aiohttp.ClientSession() as session:
            auth = aiohttp.BasicAuth(self.client_id, self.client_secret)
            
            data = {
                "grant_type": "refresh_token",
                "refresh_token": token_info.refresh_token
            }
            
            async with session.post(
                self.token_url,
                data=data,
                auth=auth
            ) as response:
                if not response.ok:
                    raise ValueError(f"Token refresh failed: {await response.text()}")
                
                token_data = await response.json()
                
                return TokenInfo(
                    access_token=token_data["access_token"],
                    token_type=token_data["token_type"],
                    expires_at=datetime.utcnow() + timedelta(seconds=token_data["expires_in"]),
                    refresh_token=token_data.get("refresh_token", token_info.refresh_token),
                    scope=token_data.get("scope", token_info.scope),
                    platform="twitter"
                )
