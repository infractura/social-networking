import pytest
import asyncio
from typing import Generator

@pytest.fixture(scope="function")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Create an instance of the default event loop for each test case."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    yield loop
    
    # Clean up pending tasks
    try:
        pending = asyncio.all_tasks(loop)
        if pending:
            loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
        loop.run_until_complete(loop.shutdown_asyncgens())
    except Exception:
        pass
    
    try:
        loop.close()
    except Exception:
        pass

@pytest.fixture
async def aiohttp_client():
    """Setup aiohttp client session for tests."""
    yield
    # Cleanup any remaining sessions
    await asyncio.sleep(0)  # Allow pending tasks to complete
