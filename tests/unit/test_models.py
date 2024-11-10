def test_social_post_string_representation():
    """Test string representation of SocialPost."""
    post = SocialPost(
        content="Test post",
        media_urls=["https://example.com/image.jpg"],
        metadata={"tag": "test"}
    )
    str_repr = str(post)
    assert "Test post" in str_repr
    assert "image.jpg" in str_repr

def test_social_post_equality():
    """Test equality comparison of SocialPost."""
    post1 = SocialPost(content="Test post")
    post2 = SocialPost(content="Test post")
    post3 = SocialPost(content="Different post")

    assert post1 == post2
    assert post1 != post3

def test_social_post_copy():
    """Test copying of SocialPost."""
    original = SocialPost(
        content="Original post",
        media_urls=["https://example.com/image.jpg"],
        metadata={"key": "value"}
    )

    # Test model_copy()
    copy = original.model_copy()
    assert copy == original
    assert copy is not original

def test_social_post_content_normalization():
    """Test content normalization."""
    # Test whitespace normalization
    post = SocialPost(content="  Test   post  ")
    assert post.content == "Test post"

    # Test newline handling
    post = SocialPost(content="Test\\npost\\n")
    assert post.content == "Test\\npost"

def test_social_post_url_validation():
    """Test URL validation in media_urls."""
    # Valid URLs
    valid_urls = [
        "https://example.com/image.jpg",
        "http://example.com/image.png",
        "https://sub.example.com/path/to/image.gif"
    ]
    post = SocialPost(content="Test", media_urls=valid_urls)
    assert len(post.media_urls) == 3

    # Invalid URLs
    invalid_urls = [
        "not-a-url",
        "ftp://example.com/image.jpg",
        "file:///path/to/image.jpg"
    ]
    for url in invalid_urls:
        with pytest.raises(ValidationError):
            SocialPost(content="Test", media_urls=[url])

def test_social_post_metadata_size_limit():
    """Test metadata size limits."""
    # Create large metadata
    large_metadata = {str(i): "x" * 1000 for i in range(100)}

    # Should raise validation error for too large metadata
    with pytest.raises(ValidationError):
        SocialPost(content="Test", metadata=large_metadata)
