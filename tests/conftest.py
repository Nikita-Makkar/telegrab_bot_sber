"""Pytest configuration and fixtures."""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime

from bot.database import Database
from bot.llm_service_unified import UnifiedLLMService


# Removed deprecated event_loop fixture - pytest-asyncio handles it automatically


@pytest.fixture
async def test_db(tmp_path):
    """Create a test database."""
    db_path = tmp_path / "test.db"
    db = Database(db_path=str(db_path))
    await db.init()
    yield db
    # Cleanup handled by tmp_path


@pytest.fixture
def mock_llm_service():
    """Create a mock LLM service."""
    service = MagicMock(spec=UnifiedLLMService)
    service.provider = "groq"  # Add provider attribute
    service.generate_code_options = AsyncMock(
        return_value=[
            "    def function_one():",
            "    def function_two():",
            "    def function_three():",
            "    def function_four():",
        ]
    )
    service.complete_code = AsyncMock(return_value="def completed():\n    pass")
    return service


@pytest.fixture
def mock_bot():
    """Create a mock Telegram bot."""
    bot = AsyncMock()
    
    # Mock poll message with both poll and message_id
    mock_poll_message = MagicMock()
    mock_poll = MagicMock()
    mock_poll.id = "test_poll_id"
    mock_poll_message.poll = mock_poll
    mock_poll_message.message_id = 12345
    
    bot.send_poll = AsyncMock(return_value=mock_poll_message)
    bot.stop_poll = AsyncMock()
    return bot


@pytest.fixture
def start_time():
    """Mock start time for uptime tracking."""
    return datetime(2024, 1, 1, 0, 0, 0)
