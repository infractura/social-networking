# Social Integrator Examples

This directory contains example scripts demonstrating how to use Social Integrator.

## Setup

1. Create a `.env` file in this directory with your credentials:
   ```bash
   cp ../.env.example .env
   # Edit .env with your credentials
   ```

2. Install dependencies:
   ```bash
   pip install -e ".."  # Install social-integrator in development mode
   pip install python-dotenv  # For .env file support
   ```

## Examples

### Basic Twitter Integration

`twitter_example.py` demonstrates basic Twitter integration:
- Posting a tweet with text and media
- Getting tweet metrics
- Deleting a tweet

```bash
./twitter_example.py
```

### Batch Processing

`batch_example.py` demonstrates batch processing with rate limiting:
- Creating multiple posts
- Processing posts in batches
- Handling rate limits
- Getting metrics for multiple posts

```bash
./batch_example.py
```
