# Integration Tests

This directory contains integration tests that interact with real social media platforms.
These tests require valid API credentials and are not run by default.

## Setup

1. Create a `.env` file in the project root with your test credentials:

```bash
SOCIAL_TWITTER__CLIENT_ID=your_test_client_id
SOCIAL_TWITTER__CLIENT_SECRET=your_test_client_secret
```

2. Install test dependencies:

```bash
pip install -e ".[dev]"
```

## Running Tests

Run integration tests using the `--run-integration` flag:

```bash
# Run all integration tests
pytest --run-integration tests/integration/

# Run specific test file
pytest --run-integration tests/integration/test_twitter.py

# Run specific test
pytest --run-integration tests/integration/test_twitter.py::test_twitter_post_lifecycle
```

## Test Categories

### Twitter Integration (`test_twitter.py`)

- `test_twitter_post_lifecycle`: Tests the complete lifecycle of a Twitter post
  - Creating a post
  - Getting metrics
  - Deleting the post

- `test_twitter_rate_limiting`: Tests rate limiting behavior
  - Creating multiple posts
  - Handling rate limits

- `test_twitter_error_handling`: Tests error handling
  - Non-existent posts
  - Duplicate posts

## Best Practices

1. Always clean up test data (delete test posts)
2. Use unique content for each test to avoid duplicates
3. Add proper error handling and assertions
4. Use test fixtures for common setup
5. Tag tests appropriately (`@pytest.mark.integration`)
