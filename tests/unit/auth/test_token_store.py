import pytest
import json
import os
from pathlib import Path
from datetime import datetime, timedelta, UTC
from social_integrator.auth.auth_manager import TokenInfo, TokenStore

@pytest.fixture
def temp_token_file(tmp_path):
    """Create a temporary token file."""
    token_file = tmp_path / "tokens.json"
    return str(token_file)

def test_token_store_basic(temp_token_file):
    """Test basic TokenStore functionality."""
    store = TokenStore(temp_token_file)
    
    # Test storing token
    token = TokenInfo(
        access_token="test_token",
        platform="test",
        expires_at=datetime.now(UTC) + timedelta(hours=1)
    )
    store.store_token(token)
    
    # Test retrieving token
    retrieved = store.get_token("test")
    assert retrieved is not None
    assert retrieved.access_token == "test_token"
    
    # Test removing token
    store.remove_token("test")
    assert store.get_token("test") is None

def test_token_store_persistence(temp_token_file):
    """Test TokenStore persistence across instances."""
    # Store token in first instance
    store1 = TokenStore(temp_token_file)
    token = TokenInfo(
        access_token="test_token",
        platform="test",
        expires_at=datetime.now(UTC) + timedelta(hours=1)
    )
    store1.store_token(token)
    
    # Retrieve in second instance
    store2 = TokenStore(temp_token_file)
    retrieved = store2.get_token("test")
    assert retrieved is not None
    assert retrieved.access_token == "test_token"

def test_token_store_invalid_json(temp_token_file):
    """Test TokenStore handling of invalid JSON."""
    # Write invalid JSON
    with open(temp_token_file, 'w') as f:
        f.write("invalid json")
    
    with pytest.raises(RuntimeError, match="Failed to load tokens"):
        TokenStore(temp_token_file)

def test_token_store_readonly(tmp_path):
    """Test TokenStore handling of read-only files."""
    # Create read-only directory
    read_only_dir = tmp_path / "readonly"
    read_only_dir.mkdir()
    token_file = read_only_dir / "tokens.json"
    
    # Create file first (so it exists)
    with open(token_file, 'w') as f:
        json.dump({}, f)
    
    # Make directory read-only after creating the file
    read_only_dir.chmod(0o555)
    token_file.chmod(0o444)  # Make file read-only too
    
    # Create store and try to save a token
    store = TokenStore(str(token_file))
    token = TokenInfo(access_token="test", platform="test")
    
    with pytest.raises(RuntimeError, match="Failed to save tokens"):
        store.store_token(token)
    
    # Cleanup for other tests
    token_file.chmod(0o644)
    read_only_dir.chmod(0o755)

def test_token_store_multiple_platforms(temp_token_file):
    """Test TokenStore handling multiple platforms."""
    store = TokenStore(temp_token_file)
    
    # Store tokens for different platforms
    platforms = ["twitter", "facebook", "instagram"]
    tokens = {}
    
    for platform in platforms:
        token = TokenInfo(
            access_token=f"{platform}_token",
            platform=platform,
            expires_at=datetime.now(UTC) + timedelta(hours=1)
        )
        store.store_token(token)
        tokens[platform] = token
    
    # Verify each platform's token
    for platform in platforms:
        retrieved = store.get_token(platform)
        assert retrieved is not None
        assert retrieved.access_token == f"{platform}_token"
        
    # Remove one platform
    store.remove_token("twitter")
    assert store.get_token("twitter") is None
    assert store.get_token("facebook") is not None

def test_token_store_update_existing(temp_token_file):
    """Test updating existing tokens in TokenStore."""
    store = TokenStore(temp_token_file)
    
    # Store initial token
    initial_token = TokenInfo(
        access_token="initial_token",
        platform="test",
        expires_at=datetime.now(UTC) + timedelta(hours=1)
    )
    store.store_token(initial_token)
    
    # Update with new token
    updated_token = TokenInfo(
        access_token="updated_token",
        platform="test",
        expires_at=datetime.now(UTC) + timedelta(hours=2)
    )
    store.store_token(updated_token)
    
    # Verify update
    retrieved = store.get_token("test")
    assert retrieved is not None
    assert retrieved.access_token == "updated_token"
