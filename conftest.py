import pytest
import sys
import asyncio
from pathlib import Path
from typing import Generator

# Add the project root to Python path
root_dir = Path(__file__).parent
sys.path.append(str(root_dir))

def pytest_configure(config):
    """Configure custom markers."""
    config.addinivalue_line(
        "markers",
        "slow: marks tests as slow (deselect with '-m \"not slow\"')"
    )
    config.addinivalue_line(
        "markers",
        "timing_sensitive: marks tests that are sensitive to timing"
    )

@pytest.fixture(scope="function")
def event_loop():
    """Create and manage event loop."""
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
