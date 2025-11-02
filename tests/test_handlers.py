"""Tests for bot handlers."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch, mock_open
from datetime import datetime
from aiogram.types import Message, User, PollAnswer, Chat

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

    await test_db.save_poll(
        chat_id, "poll1", 1, ["def func():", "class A:", "x = 1", "y = 2"], message_id=123
    )
    await test_db.close_poll("poll1", 0)

    message = MagicMock(spec=Message)
    message.chat = MagicMock()
    message.chat.id = chat_id
    message.bot = mock_bot
    message.bot.database = test_db
    message.answer = AsyncMock()

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


@pytest.mark.asyncio
async def test_cmd_start(mock_bot, test_db, mock_llm_service):
    """Test /start command handler."""
    from aiogram.fsm.context import FSMContext
    from bot.handlers import cmd_start
    from bot.poll_manager import PollManager

    Config.ADMIN_USER_IDS = [12345]

    poll_manager = PollManager(mock_bot, test_db, mock_llm_service)
    mock_bot.poll_manager = poll_manager
    mock_bot.database = test_db

    message = MagicMock(spec=Message)
    message.from_user = MagicMock(spec=User)
    message.from_user.id = 12345
    message.chat = MagicMock(spec=Chat)
    message.chat.id = 12345
    message.bot = mock_bot
    message.answer = AsyncMock()

    state = MagicMock(spec=FSMContext)

    await cmd_start(message, state)

    message.answer.assert_called_once()
    assert mock_bot.send_poll.called


@pytest.mark.asyncio
async def test_cmd_start_not_admin(mock_bot, test_db):
    """Test /start command handler - non-admin user."""
    from aiogram.fsm.context import FSMContext
    from bot.handlers import cmd_start

    Config.ADMIN_USER_IDS = [12345]

    message = MagicMock(spec=Message)
    message.from_user = MagicMock(spec=User)
    message.from_user.id = 99999
    message.answer = AsyncMock()

    state = MagicMock(spec=FSMContext)

    await cmd_start(message, state)

    message.answer.assert_called_once()
    assert "administrators" in message.answer.call_args[0][0].lower()


@pytest.mark.asyncio
async def test_cmd_code_empty_history(mock_bot, test_db):
    """Test /code command handler with empty history."""
    from aiogram.fsm.context import FSMContext
    from bot.handlers import cmd_code

    message = MagicMock(spec=Message)
    message.chat = MagicMock(spec=Chat)
    message.chat.id = 12345
    message.bot = mock_bot
    message.bot.database = test_db
    message.answer = AsyncMock()

    state = MagicMock(spec=FSMContext)

    await cmd_code(message, state)

    message.answer.assert_called_once()
    assert "No code generated" in message.answer.call_args[0][0]


@pytest.mark.asyncio
async def test_cmd_code_completed(mock_bot, test_db, mock_llm_service):
    """Test /code_completed command handler."""
    from aiogram.fsm.context import FSMContext
    from bot.handlers import cmd_code_completed

    Config.ADMIN_USER_IDS = [12345]

    chat_id = 12345

    # Save some history
    await test_db.save_poll(chat_id, "poll1", 1, ["def func():", "class A:", "x = 1", "y = 2"])
    await test_db.close_poll("poll1", 0)

    message = MagicMock(spec=Message)
    message.from_user = MagicMock(spec=User)
    message.from_user.id = 12345
    message.chat = MagicMock(spec=Chat)
    message.chat.id = chat_id
    message.bot = mock_bot
    message.bot.database = test_db
    message.bot.llm_service = mock_llm_service
    message.answer = AsyncMock()

    state = MagicMock(spec=FSMContext)

    with patch("bot.handlers.aiofiles.open", create=True) as mock_file:
        mock_file.return_value.__aenter__.return_value.read = AsyncMock(return_value=b"test code")

        await cmd_code_completed(message, state)

        assert message.answer.call_count >= 1


@pytest.mark.asyncio
async def test_cmd_code_completed_not_admin(mock_bot):
    """Test /code_completed command handler - non-admin user."""
    from aiogram.fsm.context import FSMContext
    from bot.handlers import cmd_code_completed

    Config.ADMIN_USER_IDS = [12345]

    message = MagicMock(spec=Message)
    message.from_user = MagicMock(spec=User)
    message.from_user.id = 99999
    message.answer = AsyncMock()

    state = MagicMock(spec=FSMContext)

    await cmd_code_completed(message, state)

    message.answer.assert_called_once()
    assert "administrators" in message.answer.call_args[0][0].lower()


@pytest.mark.asyncio
async def test_cmd_sendnow(mock_bot, test_db, mock_llm_service):
    """Test /sendnow command handler."""
    from aiogram.fsm.context import FSMContext
    from bot.handlers import cmd_sendnow
    from bot.poll_manager import PollManager

    Config.ADMIN_USER_IDS = [12345]

    poll_manager = PollManager(mock_bot, test_db, mock_llm_service)
    mock_bot.poll_manager = poll_manager
    mock_bot.database = test_db

    message = MagicMock(spec=Message)
    message.from_user = MagicMock(spec=User)
    message.from_user.id = 12345
    message.chat = MagicMock(spec=Chat)
    message.chat.id = 12345
    message.bot = mock_bot
    message.answer = AsyncMock()

    state = MagicMock(spec=FSMContext)

    await cmd_sendnow(message, state)

    assert message.answer.called
    assert mock_bot.send_poll.called


@pytest.mark.asyncio
async def test_cmd_sendnow_with_active_poll(mock_bot, test_db, mock_llm_service):
    """Test /sendnow command handler with active poll."""
    from aiogram.fsm.context import FSMContext
    from bot.handlers import cmd_sendnow
    from bot.poll_manager import PollManager

    Config.ADMIN_USER_IDS = [12345]

    chat_id = 12345
    poll_manager = PollManager(mock_bot, test_db, mock_llm_service)
    mock_bot.poll_manager = poll_manager
    mock_bot.database = test_db

    # Create active poll
    await test_db.save_poll(chat_id, "active_poll", 1, ["a", "b", "c", "d"])

    message = MagicMock(spec=Message)
    message.from_user = MagicMock(spec=User)
    message.from_user.id = 12345
    message.chat = MagicMock(spec=Chat)
    message.chat.id = chat_id
    message.bot = mock_bot
    message.answer = AsyncMock()

    state = MagicMock(spec=FSMContext)

    await cmd_sendnow(message, state)

    message.answer.assert_called_once()
    assert "active poll" in message.answer.call_args[0][0].lower()


@pytest.mark.asyncio
async def test_cmd_health(mock_bot, test_db, mock_llm_service):
    """Test /health command handler."""
    from aiogram.fsm.context import FSMContext
    from bot.handlers import cmd_health
    from bot.poll_manager import PollManager

    Config.ADMIN_USER_IDS = [12345]

    poll_manager = PollManager(mock_bot, test_db, mock_llm_service)
    mock_bot.poll_manager = poll_manager
    mock_bot.database = test_db
    mock_bot.start_time = datetime.now()

    message = MagicMock(spec=Message)
    message.from_user = MagicMock(spec=User)
    message.from_user.id = 12345
    message.chat = MagicMock(spec=Chat)
    message.chat.id = 12345
    message.bot = mock_bot
    message.answer = AsyncMock()

    state = MagicMock(spec=FSMContext)

    await cmd_health(message, state)

    message.answer.assert_called_once()
    assert "Bot Health Status" in message.answer.call_args[0][0]


@pytest.mark.asyncio
async def test_cmd_logs(mock_bot):
    """Test /logs command handler."""
    from bot.handlers import cmd_logs

    Config.ADMIN_USER_IDS = [12345]

    message = MagicMock(spec=Message)
    message.from_user = MagicMock(spec=User)
    message.from_user.id = 12345
    message.answer = AsyncMock()

    with patch("bot.handlers.os.path.exists", return_value=True):
        with patch("builtins.open", mock_open(read_data="line1\nline2\nline3\n")):
            await cmd_logs(message)

            message.answer.assert_called_once()


@pytest.mark.asyncio
async def test_cmd_logs_no_file(mock_bot):
    """Test /logs command handler with no log file."""
    from bot.handlers import cmd_logs

    Config.ADMIN_USER_IDS = [12345]

    message = MagicMock(spec=Message)
    message.from_user = MagicMock(spec=User)
    message.from_user.id = 12345
    message.answer = AsyncMock()

    with patch("bot.handlers.os.path.exists", return_value=False):
        await cmd_logs(message)

        message.answer.assert_called_once()
        assert "No log file" in message.answer.call_args[0][0]


@pytest.mark.asyncio
async def test_cmd_alllogs(mock_bot):
    """Test /alllogs command handler."""
    from bot.handlers import cmd_alllogs

    Config.ADMIN_USER_IDS = [12345]

    message = MagicMock(spec=Message)
    message.from_user = MagicMock(spec=User)
    message.from_user.id = 12345
    message.answer_document = AsyncMock()

    mock_file = AsyncMock()
    mock_file.read = AsyncMock(return_value=b"log content")

    with patch("bot.handlers.os.path.exists", return_value=True):
        with patch("bot.handlers.aiofiles.open", create=True) as mock_aiofiles:
            mock_aiofiles.return_value.__aenter__.return_value = mock_file
            await cmd_alllogs(message)

            message.answer_document.assert_called_once()


@pytest.mark.asyncio
async def test_handle_poll_answer_empty_option_ids(mock_bot, test_db, mock_llm_service):
    """Test poll answer handler with empty option_ids."""
    from bot.handlers import handle_poll_answer
    from bot.poll_manager import PollManager

    poll_manager = PollManager(mock_bot, test_db, mock_llm_service)
    mock_bot.poll_manager = poll_manager

    poll_answer = MagicMock(spec=PollAnswer)
    poll_answer.poll_id = "test_poll"
    poll_answer.user = MagicMock(spec=User)
    poll_answer.user.id = 123
    poll_answer.option_ids = []
    poll_answer.bot = mock_bot

    await handle_poll_answer(poll_answer)
