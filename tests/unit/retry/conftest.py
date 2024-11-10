import pytest
from unittest.mock import AsyncMock, MagicMock
from social_integrator.platforms.twitter import TwitterAPI
from social_integrator.core.platform import SocialPost

@pytest.fixture
def twitter_api():
    """Create a TwitterAPI instance."""
    return TwitterAPI(auth_token="test_token")

@pytest.fixture
def social_post():
    """Create a test social post."""
    return SocialPost(content="Test post")
