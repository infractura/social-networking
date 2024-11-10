from typing import Dict, Optional
from pydantic_settings import BaseSettings
from pydantic import BaseModel, ConfigDict

class PlatformConfig(BaseModel):
    """Base configuration for social media platforms."""
    rate_limit_calls: int = 300
    rate_limit_period: float = 900.0  # 15 minutes
    retry_count: int = 3
    timeout: float = 30.0

    model_config = ConfigDict(frozen=True)

    @property
    def max_retries(self) -> int:
        """Alias for retry_count for backward compatibility."""
        return self.retry_count

class TwitterConfig(PlatformConfig):
    """Twitter-specific configuration."""
    api_base_url: str = "https://api.twitter.com/2"
    media_upload_url: str = "https://upload.twitter.com/1.1/media/upload.json"

class Settings(BaseSettings):
    """Global settings."""
    debug: bool = False
    platform_configs: Dict[str, PlatformConfig] = {
        "twitter": TwitterConfig()
    }

    model_config = ConfigDict(
        env_prefix="SOCIAL_",
        frozen=True
    )

def get_platform_config(platform: str) -> Optional[PlatformConfig]:
    """Get configuration for a specific platform."""
    settings = Settings()
    return settings.platform_configs.get(platform)
