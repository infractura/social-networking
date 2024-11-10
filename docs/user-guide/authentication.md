# Authentication Guide

Learn how to handle authentication in Social Integrator.

## Overview

Social Integrator provides a robust authentication system that:

- Manages OAuth 2.0 flows
- Securely stores tokens
- Automatically refreshes expired tokens
- Handles token revocation

## Twitter Authentication

### Setup

1. Create a Twitter Developer Account
2. Create a Project and App
3. Get your OAuth 2.0 credentials:
   - Client ID
   - Client Secret

### Implementation

```python
from social_integrator import SocialIntegrator

# Initialize the integrator
integrator = SocialIntegrator()

# Configure Twitter OAuth
integrator.configure_twitter(
    client_id="your_client_id",
    client_secret="your_client_secret",
    redirect_uri="http://localhost:8080/callback",
    scopes=[
        "tweet.read",
        "tweet.write",
        "users.read",
        "offline.access"
    ]
)
```

### Token Management

Tokens are automatically managed:

```python
async def example_token_management():
    async with integrator:
        # Token is automatically obtained/refreshed
        await integrator.post("twitter", post)

    # Explicitly manage tokens
    token_info = await integrator.auth_manager.get_valid_token("twitter")
    print(f"Access token: {token_info.access_token}")

    # Revoke tokens
    integrator.auth_manager.revoke_token("twitter")
```

## Token Storage

By default, tokens are stored in `~/.social_integrator/tokens.json`. You can customize this:

```python
from social_integrator.auth import TokenStore

# Custom token storage location
token_store = TokenStore("/path/to/tokens.json")
integrator.auth_manager.token_store = token_store
```

## Security Best Practices

1. Never commit credentials to version control
2. Use environment variables or secure vaults for secrets
3. Implement proper PKCE for OAuth flows
4. Regularly rotate refresh tokens
5. Use HTTPS for all API communications
