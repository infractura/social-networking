import pytest
import asyncio
from typing import AsyncGenerator
import warnings

@pytest.fixture(scope="function")
async def event_loop() -> AsyncGenerator[asyncio.AbstractEventLoop, None]:
    """Create an instance of the default event loop for each test case."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    # Enable debug mode for better error messages
    loop.set_debug(True)
    
    yield loop
    
    # Clean up pending tasks
    pending = asyncio.all_tasks(loop)
    if pending:
        # Give tasks a chance to complete
        await asyncio.gather(*pending, return_exceptions=True)
        
        # Cancel any remaining tasks
        for task in pending:
            if not task.done():
                task.cancel()
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore", RuntimeWarning)
                    try:
                        await task
                    except asyncio.CancelledError:
                        pass
    
    await loop.shutdown_asyncgens()
    await asyncio.sleep(0)  # Final cleanup
    loop.close()

@pytest.fixture
async def batcher_cleanup():
    """Cleanup fixture for AsyncBatcher tests."""
    yield
    # Clean up any remaining tasks
    loop = asyncio.get_event_loop()
    pending = asyncio.all_tasks(loop)
    for task in pending:
        if not task.done() and task.get_name().startswith('AsyncBatcher'):
            task.cancel()
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", RuntimeWarning)
                try:
                    await task
                except asyncio.CancelledError:
                    pass
