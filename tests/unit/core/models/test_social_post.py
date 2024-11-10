import pytest
from social_integrator.core.platform import SocialPost
from pydantic import ValidationError

def test_social_post_basic():
    """Test basic SocialPost creation and properties."""
    post = SocialPost(content="Test post")
    assert post.content == "Test post"
    assert len(post.media_urls) == 0
    assert len(post.metadata) == 0

def test_social_post_with_media():
    """Test SocialPost with media URLs."""
    media_urls = [
        "http://example.com/image1.jpg",
        "http://example.com/image2.jpg"
    ]
    post = SocialPost(
        content="Test with media",
        media_urls=media_urls
    )
    assert post.content == "Test with media"
    assert len(post.media_urls) == len(media_urls)
    assert all(a == b for a, b in zip(post.media_urls, media_urls))

def test_social_post_with_metadata():
    """Test SocialPost with metadata."""
    metadata = {
        "visibility": "public",
        "category": "test",
        "tags": ["test", "example"]
    }
    post = SocialPost(
        content="Test with metadata",
        metadata=metadata
    )
    assert post.content == "Test with metadata"
    assert dict(post.metadata) == metadata
    assert post.metadata["visibility"] == "public"

def test_social_post_validation():
    """Test SocialPost validation rules."""
    # Empty content should raise error
    with pytest.raises(ValidationError):
        SocialPost(content="")
    
    # None content should raise error
    with pytest.raises(ValidationError):
        SocialPost(content=None)
    
    # Whitespace-only content should raise error
    with pytest.raises(ValidationError):
        SocialPost(content="   ")

def test_social_post_media_validation():
    """Test validation of media URLs."""
    # Invalid media URL format
    with pytest.raises(ValidationError):
        SocialPost(
            content="Test post",
            media_urls=["not_a_url"]
        )
    
    # Empty media URL
    with pytest.raises(ValidationError):
        SocialPost(
            content="Test post",
            media_urls=[""]
        )

def test_social_post_metadata_validation():
    """Test validation of metadata."""
    # Non-dict metadata
    with pytest.raises(ValidationError):
        SocialPost(
            content="Test post",
            metadata=["not", "a", "dict"]
        )

def test_social_post_equality():
    """Test SocialPost equality comparison."""
    post1 = SocialPost(
        content="Test post",
        media_urls=["http://example.com/image.jpg"],
        metadata={"key": "value"}
    )
    post2 = SocialPost(
        content="Test post",
        media_urls=["http://example.com/image.jpg"],
        metadata={"key": "value"}
    )
    post3 = SocialPost(
        content="Different post",
        media_urls=["http://example.com/image.jpg"],
        metadata={"key": "value"}
    )
    
    assert post1 == post2
    assert post1 != post3
    assert post1 != "not a post"

def test_social_post_immutability():
    """Test that SocialPost attributes are immutable."""
    post = SocialPost(
        content="Test post",
        media_urls=["http://example.com/image.jpg"],
        metadata={"key": "value"}
    )
    
    # Attempt to modify attributes
    with pytest.raises(ValidationError):
        post.content = "Changed content"
    
    # Verify media_urls is immutable
    with pytest.raises(ValidationError):
        post.media_urls = ["new_url"]
    
    # Verify metadata is immutable
    with pytest.raises(ValidationError):
        post.metadata = {"new": "value"}
    
    # Verify collections are immutable
    with pytest.raises((AttributeError, TypeError)):
        post.media_urls[0] = "new_url"
    with pytest.raises((AttributeError, TypeError)):
        post.metadata["new"] = "value"

def test_social_post_valid_urls():
    """Test valid URL formats."""
    valid_urls = [
        "http://example.com",
        "https://example.com/image.jpg",
        "http://localhost:8080/test",
        "https://sub.domain.com/path/to/image?param=value",
        "http://192.168.1.1/test.png"
    ]
    
    post = SocialPost(
        content="Test post",
        media_urls=valid_urls
    )
    assert len(post.media_urls) == len(valid_urls)
    assert all(a == b for a, b in zip(post.media_urls, valid_urls))

def test_social_post_invalid_urls():
    """Test invalid URL formats."""
    invalid_urls = [
        "not_a_url",
        "ftp://example.com",
        "//no-protocol.com",
        "http:/missing-slash.com",
        ""
    ]
    
    for url in invalid_urls:
        with pytest.raises(ValidationError):
            SocialPost(
                content="Test post",
                media_urls=[url]
            )
