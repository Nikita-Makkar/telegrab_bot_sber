"""Tests for bot handlers."""

import pytest
from unittest.mock import AsyncMock, MagicMock
from aiogram.types import Message, User, PollAnswer

from bot.handlers import is_admin
from bot.config import Config


def test_is_admin():
    """Test admin check."""
    # Set a test admin ID
    Config.ADMIN_USER_IDS = [12345]

    assert is_admin(12345) is True
    assert is_admin(99999) is False


@pytest.mark.asyncio
async def test_cmd_code(mock_bot, test_db):
    """Test /code command handler."""
    from aiogram.fsm.context import FSMContext
    from bot.handlers import cmd_code

    chat_id = 12345

    # Save some history
    await test_db.save_poll(chat_id, "poll1", 1, ["def func():", "class A:", "x = 1", "y = 2"], message_id=123)
    await test_db.close_poll("poll1", 0)

    # Create mock message with proper chat attribute
    message = MagicMock(spec=Message)
    message.chat = MagicMock()
    message.chat.id = chat_id
    message.bot = mock_bot
    message.bot.database = test_db
    message.answer = AsyncMock()
    
    # Mock state
    state = MagicMock(spec=FSMContext)

    await cmd_code(message, state)

    message.answer.assert_called_once()
    call_args = message.answer.call_args[0][0]
    assert "def func():" in call_args


@pytest.mark.asyncio
async def test_handle_poll_answer_handler(mock_bot, test_db, mock_llm_service):
    """Test poll answer handler."""
    from bot.handlers import handle_poll_answer
    from bot.poll_manager import PollManager

    poll_manager = PollManager(mock_bot, test_db, mock_llm_service)

    poll_id = "test_poll"
    await test_db.save_poll(12345, poll_id, 1, ["a", "b", "c", "d"], message_id=123)

    # Create mock poll answer with bot attribute
    poll_answer = MagicMock(spec=PollAnswer)
    poll_answer.poll_id = poll_id
    poll_answer.user = MagicMock(spec=User)
    poll_answer.user.id = 123
    poll_answer.option_ids = [1]
    poll_answer.bot = mock_bot
    poll_answer.bot.poll_manager = poll_manager

    await handle_poll_answer(poll_answer)

    # Check vote was saved
    vote_counts = await test_db.get_vote_counts(poll_id)
    assert 1 in vote_counts
