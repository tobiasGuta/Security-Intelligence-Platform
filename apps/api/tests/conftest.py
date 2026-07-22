import sys
import os
import pytest
from pathlib import Path

# Add /app to sys.path
root_dir = Path(__file__).parent.parent
sys.path.insert(0, str(root_dir))

@pytest.fixture
def event_loop():
    import asyncio
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture
def settings():
    pass

@pytest.fixture
def test_app():
    pass

@pytest.fixture
def test_client():
    pass

@pytest.fixture
def db_session():
    pass

@pytest.fixture
def redis_client():
    pass
