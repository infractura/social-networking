from typing import Dict, List, Any, Optional, Sequence, Mapping
from datetime import datetime
import re
import types
from pydantic import BaseModel, field_validator, ConfigDict, model_validator

class SocialPost(BaseModel):
    """Social media post model."""
    content: str
    media_urls: Sequence[str] = []
    metadata: Mapping[str, Any] = {}

    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)

    @field_validator('content')
    @classmethod
    def content_not_empty(cls, v: str) -> str:
        """Validate that content is not empty."""
        if not v or not v.strip():
            raise ValueError("Content cannot be empty")
        return v

    @field_validator('media_urls')
    @classmethod
    def valid_media_urls(cls, v: Sequence[str]) -> Sequence[str]:
        """Validate media URLs."""
        url_pattern = re.compile(
            r'^https?://'  # http:// or https://
            r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain...
            r'localhost|'  # localhost...
            r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
            r'(?::\d+)?'  # optional port
            r'(?:/?|[/?]\S+)$', re.IGNORECASE)
        
        for url in v:
            if not url or not url_pattern.match(url):
                raise ValueError(f"Invalid media URL: {url}")
        return tuple(v)  # Convert to immutable tuple

    @field_validator('metadata')
    @classmethod
    def validate_metadata(cls, v: Any) -> Mapping[str, Any]:
        """Validate metadata is a mapping."""
        if isinstance(v, (dict, Mapping)):
            return types.MappingProxyType(dict(v))
        raise ValueError("Metadata must be a dictionary")

    @model_validator(mode='before')
    @classmethod
    def validate_collections(cls, values: Dict[str, Any]) -> Dict[str, Any]:
        """Validate and convert collections to immutable types."""
        if 'media_urls' in values:
            values['media_urls'] = tuple(values['media_urls'])
        if 'metadata' in values:
            if not isinstance(values['metadata'], (dict, Mapping)):
                raise ValueError("Metadata must be a dictionary")
            values['metadata'] = types.MappingProxyType(dict(values['metadata']))
        return values

class PlatformError(Exception):
    """Base exception for platform errors."""
    pass

class RateLimitError(PlatformError):
    """Rate limit exceeded error."""
    def __init__(self, message: str, retry_after: Optional[float] = None):
        super().__init__(message)
        self.retry_after = retry_after

class SocialPlatform:
    """Base class for social media platforms."""
    
    def __init__(self, auth_token: str):
        """Initialize platform.
        
        Args:
            auth_token: Authentication token
        """
        self.auth_token = auth_token
        self._initialize()
    
    def _initialize(self) -> None:
        """Platform-specific initialization."""
        raise NotImplementedError
    
    async def post(self, post: SocialPost) -> Dict[str, Any]:
        """Create a post.
        
        Args:
            post: Post content and metadata
            
        Returns:
            Platform-specific response
        """
        raise NotImplementedError
    
    async def delete_post(self, post_id: str) -> bool:
        """Delete a post.
        
        Args:
            post_id: Platform-specific post identifier
            
        Returns:
            True if deletion was successful
        """
        raise NotImplementedError
    
    async def get_post(self, post_id: str) -> Dict[str, Any]:
        """Get post details.
        
        Args:
            post_id: Platform-specific post identifier
            
        Returns:
            Post details
        """
        raise NotImplementedError
    
    async def get_metrics(self, post_id: str) -> Dict[str, Any]:
        """Get post metrics.
        
        Args:
            post_id: Platform-specific post identifier
            
        Returns:
            Post metrics
        """
        raise NotImplementedError
