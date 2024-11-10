#!/usr/bin/env python3

import asyncio
import os
from dotenv import load_dotenv

from social_integrator import SocialIntegrator, SocialPost

# Load environment variables from .env file
load_dotenv()

async def main():
    # Initialize the integrator
    integrator = SocialIntegrator()

    # Configure Twitter with environment variables
    integrator.configure_twitter(
        client_id=os.getenv("SOCIAL_TWITTER__CLIENT_ID"),
        client_secret=os.getenv("SOCIAL_TWITTER__CLIENT_SECRET")
    )

    # Create a post with text and media
    post = SocialPost(
        content="Hello from Social Integrator! 🌍 #Python #SocialMedia",
        media_urls=["https://example.com/image.jpg"],
        metadata={
            "tags": ["python", "social"]
        }
    )

    try:
        async with integrator:
            # Post to Twitter
            result = await integrator.post("twitter", post)
            print(f"Posted to Twitter: {result}")

            # Get post metrics
            post_id = result["data"]["id"]
            metrics = await integrator.get_metrics("twitter", post_id)
            print(f"Post metrics: {metrics}")

            # Delete the post
            deleted = await integrator.delete_post("twitter", post_id)
            print(f"Post deleted: {deleted}")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(main())
