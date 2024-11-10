import pytest
from datetime import datetime, timedelta, UTC
from social_integrator.auth.auth_manager import TokenInfo

def test_token_info_basic():
    """Test basic TokenInfo functionality."""
    token = TokenInfo(
        access_token="test_token",
        platform="test"
    )
    assert token.access_token == "test_token"
    assert token.token_type == "Bearer"
    assert token.platform == "test"
    assert not token.is_expired

def test_token_info_expiration():
    """Test token expiration functionality."""
    # Test expired token
    expired_token = TokenInfo(
        access_token="test_token",
        platform="test",
        expires_at=datetime.now(UTC) - timedelta(hours=1)
    )
    assert expired_token.is_expired
    
    # Test future token
    future_token = TokenInfo(
        access_token="test_token",
        platform="test",
        expires_at=datetime.now(UTC) + timedelta(hours=1)
    )
    assert not future_token.is_expired

def test_token_info_optional_fields():
    """Test TokenInfo with optional fields."""
    token = TokenInfo(
        access_token="test_token",
        platform="test",
        token_type="Custom",
        refresh_token="refresh_token",
        expires_at=datetime.now(UTC) + timedelta(hours=1)
    )
    assert token.token_type == "Custom"
    assert token.refresh_token == "refresh_token"
    assert not token.is_expired

def test_token_info_equality():
    """Test TokenInfo equality comparison."""
    token1 = TokenInfo(
        access_token="test_token",
        platform="test"
    )
    token2 = TokenInfo(
        access_token="test_token",
        platform="test"
    )
    token3 = TokenInfo(
        access_token="different_token",
        platform="test"
    )
    
    assert token1 == token2
    assert token1 != token3
    assert token1 != "not a token"
