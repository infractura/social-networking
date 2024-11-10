#!/usr/bin/env python3

import asyncio
import os
from dotenv import load_dotenv

from social_integrator import SocialIntegrator, SocialPost
from social_integrator.utils.rate_limiting import AsyncBatcher

load_dotenv()

async def main():
    integrator = SocialIntegrator()
    integrator.configure_twitter(
        client_id=os.getenv("SOCIAL_TWITTER__CLIENT_ID"),
        client_secret=os.getenv("SOCIAL_TWITTER__CLIENT_SECRET")
    )

    # Create multiple posts
    posts = [
        SocialPost(
            content=f"Batch post #{i} from Social Integrator! 🚀",
            metadata={"batch_id": i}
        )
        for i in range(5)  # Create 5 posts
    ]

    async with integrator:
        # Get the Twitter platform instance
        twitter = await integrator.get_platform("twitter")

        # Create a batcher with rate limiting
        batcher = AsyncBatcher(
            batch_size=2,  # Process 2 posts at a time
            flush_interval=60.0,  # Auto-flush after 60 seconds
            rate_limiter=twitter.rate_limiter
        )

        # Process posts in batches
        results = []
        for post in posts:
            try:
                # Add post to batch
                await batcher.add(post)
                print(f"Added post to batch: {post.content}")
            except Exception as e:
                print(f"Error adding post to batch: {e}")

        # Ensure all remaining posts are processed
        await batcher.flush()

        # Get metrics for all posts
        for result in results:
            try:
                post_id = result["data"]["id"]
                metrics = await twitter.get_metrics(post_id)
                print(f"Metrics for post {post_id}: {metrics}")
            except Exception as e:
                print(f"Error getting metrics: {e}")

if __name__ == "__main__":
    asyncio.run(main())
