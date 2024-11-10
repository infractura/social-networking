import pytest
from typing import Dict, Any
from social_integrator.core.platform import (
    SocialPlatform,
    SocialPost,
    PlatformError
)

class MockPlatform(SocialPlatform):
    """Mock platform implementation for testing."""
    
    def __init__(self, auth_token: str, should_fail: bool = False):
        self.should_fail = should_fail
        self.posts: Dict[str, SocialPost] = {}
        self.post_counter = 0
        super().__init__(auth_token=auth_token)
    
    def _initialize(self) -> None:
        """Mock initialization."""
        pass
    
    async def post(self, post: SocialPost) -> Dict[str, Any]:
        """Mock post creation."""
        if self.should_fail:
            raise PlatformError("Mock platform error")
        
        self.post_counter += 1
        post_id = f"mock_post_{self.post_counter}"
        self.posts[post_id] = post
        
        return {
            "id": post_id,
            "platform": "mock",
            "status": "posted"
        }
    
    async def delete_post(self, post_id: str) -> bool:
        """Mock post deletion."""
        if self.should_fail:
            raise PlatformError("Mock platform error")
        
        if post_id in self.posts:
            del self.posts[post_id]
            return True
        return False
    
    async def get_post(self, post_id: str) -> Dict[str, Any]:
        """Mock post retrieval."""
        if self.should_fail:
            raise PlatformError("Mock platform error")
        
        if post_id not in self.posts:
            return {}
        
        post = self.posts[post_id]
        return {
            "id": post_id,
            "content": post.content,
            "media_urls": post.media_urls,
            "metadata": post.metadata
        }
    
    async def get_metrics(self, post_id: str) -> Dict[str, Any]:
        """Mock metrics retrieval."""
        if self.should_fail:
            raise PlatformError("Mock platform error")
        
        if post_id not in self.posts:
            raise PlatformError("Post not found")
        
        return {
            "likes": 42,
            "shares": 7,
            "comments": 3
        }

@pytest.fixture
def mock_platform():
    """Create a mock platform instance."""
    return MockPlatform(auth_token="mock_token")

@pytest.fixture
def failing_mock_platform():
    """Create a mock platform instance that fails operations."""
    return MockPlatform(auth_token="mock_token", should_fail=True)

@pytest.fixture
def sample_post():
    """Create a sample social post."""
    return SocialPost(
        content="Test post",
        media_urls=["http://example.com/image.jpg"],
        metadata={"key": "value"}
    )
