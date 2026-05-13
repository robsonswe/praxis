import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.database import set_db_path, close_connection


@pytest.fixture(autouse=True)
async def use_memory_db():
    await close_connection()
    set_db_path(":memory:")
    yield
    await close_connection()