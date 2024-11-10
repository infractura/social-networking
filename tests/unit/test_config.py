import pytest
from pydantic import ValidationError

from social_integrator.core.config import Settings, PlatformConfig, TwitterConfig

def test_platform_config_validation():
    """Test PlatformConfig validation."""
    # Valid config
    config = PlatformConfig(
        api_base_url="https://api.example.com",
        rate_limit_calls=100,
        rate_limit_period=900.0
    )
    assert config.api_base_url == "https://api.example.com"
    assert config.rate_limit_calls == 100

    # Invalid rate limit values
    with pytest.raises(ValidationError):
        PlatformConfig(
            api_base_url="https://api.example.com",
            rate_limit_calls=-1  # Negative calls not allowed
        )

    with pytest.raises(ValidationError):
        PlatformConfig(
            api_base_url="https://api.example.com",
            rate_limit_period=-1.0  # Negative period not allowed
        )

def test_twitter_config():
    """Test TwitterConfig defaults and validation."""
    config = TwitterConfig()
    
    # Check default values
    assert config.api_base_url == "https://api.twitter.com/2"
    assert config.rate_limit_calls == 300
    assert config.rate_limit_period == 900.0
    assert config.media_upload_url == "https://upload.twitter.com/1.1/media/upload.json"

    # Override defaults
    custom_config = TwitterConfig(
        rate_limit_calls=100,
        rate_limit_period=300.0
    )
    assert custom_config.rate_limit_calls == 100

def test_settings():
    """Test global Settings configuration."""
    settings = Settings()
    
    # Check default values
    assert settings.debug is False
    assert "twitter" in settings.platform_configs
    assert isinstance(settings.platform_configs["twitter"], TwitterConfig)

    # Custom settings
    custom_settings = Settings(
        debug=True,
        platform_configs={
            "twitter": TwitterConfig(rate_limit_calls=50)
        }
    )
    assert custom_settings.debug is True
    assert custom_settings.platform_configs["twitter"].rate_limit_calls == 50

def test_settings_env_vars(monkeypatch):
    """Test settings from environment variables."""
    # Set environment variables
    monkeypatch.setenv("SOCIAL_DEBUG", "true")
    monkeypatch.setenv("SOCIAL_TWITTER__RATE_LIMIT_CALLS", "150")

    settings = Settings()
    assert settings.debug is True
    assert settings.platform_configs["twitter"].rate_limit_calls == 150

def test_get_platform_config():
    """Test get_platform_config utility function."""
    from social_integrator.core.config import get_platform_config

    # Get existing platform config
    config = get_platform_config("twitter")
    assert isinstance(config, TwitterConfig)

    # Get non-existent platform config
    config = get_platform_config("nonexistent")
    assert config is None
