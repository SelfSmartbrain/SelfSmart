"""Pytest configuration and fixtures."""
import pytest
import asyncio
from pathlib import Path
import tempfile
from unittest.mock import patch

import pytest_asyncio
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.ext.compiler import compiles

from src.db.models import Base, Objective, ObjectiveCheckpoint, ObjectiveProgress


@compiles(JSONB, "sqlite")
def compile_jsonb_for_sqlite(_type, compiler, **kwargs):
    """Use SQLite JSON storage for PostgreSQL JSONB in isolated unit tests."""
    return "JSON"


@pytest_asyncio.fixture
async def mock_db_session():
    """Provide a fresh transactional database for runtime persistence tests."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    tables = [Objective.__table__, ObjectiveProgress.__table__, ObjectiveCheckpoint.__table__]
    async with engine.begin() as connection:
        await connection.run_sync(
            lambda sync_connection: Base.metadata.create_all(sync_connection, tables=tables)
        )

    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        yield session

    await engine.dispose()


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def temp_dir():
    """Create temporary directory for test files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def temp_config_file(temp_dir):
    """Temporary config file path."""
    return temp_dir / "config.json"


@pytest.fixture
def temp_conversation_file(temp_dir):
    """Temporary conversation file path."""
    return temp_dir / "conversation.json"


@pytest.fixture
def mock_audio_devices():
    """Mock sounddevice for testing without hardware."""
    with patch("sounddevice.query_devices") as mock_query:
        mock_query.return_value = [
            {"name": "Test Mic", "max_input_channels": 1, "max_output_channels": 0},
            {"name": "Test Speaker", "max_input_channels": 0, "max_output_channels": 2},
        ]
        with patch("sounddevice.default.device", (0, 1)):
            yield


# Markers
def pytest_configure(config):
    config.addinivalue_line("markers", "audio: marks tests as requiring audio hardware")
    config.addinivalue_line("markers", "integration: marks tests as integration tests")
    config.addinivalue_line("markers", "slow: marks tests as slow")
    config.addinivalue_line("markers", "unit: marks tests as unit tests")


# Async test support
pytest_plugins = ("pytest_asyncio",)
