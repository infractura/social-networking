import pytest
from social_integrator.core.config import (
    Settings,
    PlatformConfig,
    TwitterConfig,
    get_platform_config
)

def test_settings_defaults():
    """Test default settings configuration."""
    settings = Settings()
    
    # Test basic settings
    assert settings.debug is False
    assert isinstance(settings.platform_configs, dict)
    assert "twitter" in settings.platform_configs

def test_twitter_config_defaults():
    """Test Twitter platform configuration defaults."""
    settings = Settings()
    twitter_config = settings.platform_configs["twitter"]
    
    assert isinstance(twitter_config, TwitterConfig)
    assert twitter_config.api_base_url == "https://api.twitter.com/2"
    assert twitter_config.rate_limit_calls == 300
    assert twitter_config.rate_limit_period == 900.0  # 15 minutes
    assert twitter_config.retry_count == 3
    assert twitter_config.max_retries == 3  # Should match retry_count

def test_platform_config_validation():
    """Test platform configuration validation."""
    # Test valid config
    config = PlatformConfig(
        rate_limit_calls=100,
        rate_limit_period=300.0,
        retry_count=5
    )
    assert config.rate_limit_calls == 100
    assert config.rate_limit_period == 300.0
    assert config.retry_count == 5

def test_get_platform_config():
    """Test platform configuration retrieval."""
    # Test existing platform
    config = get_platform_config("twitter")
    assert isinstance(config, TwitterConfig)
    assert config.api_base_url == "https://api.twitter.com/2"
    
    # Test nonexistent platform
    assert get_platform_config("nonexistent") is None

def test_platform_config_custom_values():
    """Test platform configuration with custom values."""
    custom_config = PlatformConfig(
        rate_limit_calls=100,
        rate_limit_period=300.0,
        retry_count=5
    )
    
    assert custom_config.rate_limit_calls == 100
    assert custom_config.rate_limit_period == 300.0
    assert custom_config.retry_count == 5
    assert custom_config.max_retries == 5

def test_twitter_config_custom_values():
    """Test Twitter configuration with custom values."""
    custom_config = TwitterConfig(
        api_base_url="https://custom.twitter.api",
        rate_limit_calls=100,
        rate_limit_period=300.0,
        retry_count=5
    )
    
    assert custom_config.api_base_url == "https://custom.twitter.api"
    assert custom_config.rate_limit_calls == 100
    assert custom_config.rate_limit_period == 300.0
    assert custom_config.retry_count == 5
    assert custom_config.max_retries == 5

def test_settings_override():
    """Test settings override functionality."""
    custom_twitter_config = TwitterConfig(
        api_base_url="https://custom.twitter.api",
        rate_limit_calls=100
    )
    
    settings = Settings(
        debug=True,
        platform_configs={
            "twitter": custom_twitter_config
        }
    )
    
    assert settings.debug is True
    assert settings.platform_configs["twitter"].api_base_url == "https://custom.twitter.api"
    assert settings.platform_configs["twitter"].rate_limit_calls == 100

def test_platform_config_immutability():
    """Test that platform configurations are immutable."""
    config = PlatformConfig()
    
    with pytest.raises(Exception):  # Pydantic v2 raises different exception types
        config.rate_limit_calls = 200
    
    with pytest.raises(Exception):
        config.rate_limit_period = 600.0
    
    with pytest.raises(Exception):
        config.retry_count = 10

def test_twitter_config_immutability():
    """Test that Twitter configuration is immutable."""
    config = TwitterConfig()
    
    with pytest.raises(Exception):  # Pydantic v2 raises different exception types
        config.api_base_url = "https://new.api.url"
    
    with pytest.raises(Exception):
        config.rate_limit_calls = 200

def test_platform_config_equality():
    """Test platform configuration equality comparison."""
    config1 = PlatformConfig(rate_limit_calls=100, rate_limit_period=300.0)
    config2 = PlatformConfig(rate_limit_calls=100, rate_limit_period=300.0)
    config3 = PlatformConfig(rate_limit_calls=200, rate_limit_period=300.0)
    
    assert config1 == config2
    assert config1 != config3
    assert config1 != "not a config"
