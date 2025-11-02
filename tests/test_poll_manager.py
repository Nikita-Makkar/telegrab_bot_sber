"""Tests for poll manager."""

import asyncio
import pytest
from unittest.mock import AsyncMock

from bot.poll_manager import PollManager


@pytest.mark.asyncio
async def test_create_poll(test_db, mock_bot, mock_llm_service):
    """Test creating a poll."""
    poll_manager = PollManager(mock_bot, test_db, mock_llm_service)

    chat_id = 12345

    poll_id = await poll_manager.create_poll(chat_id)

    assert poll_id is not None
    assert poll_id == "test_poll_id"
    mock_bot.send_poll.assert_called_once()
    assert len(poll_manager.active_polls) == 1

    for task in poll_manager.active_polls.values():
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass


@pytest.mark.asyncio
async def test_handle_poll_answer(test_db, mock_bot, mock_llm_service):
    """Test handling poll answer."""
    poll_manager = PollManager(mock_bot, test_db, mock_llm_service)

    poll_id = "test_poll"
    user_id = 123
    option_ids = [1]

    await test_db.save_poll(12345, poll_id, 1, ["a", "b", "c", "d"])

    await poll_manager.handle_poll_answer(poll_id, user_id, option_ids)

    vote_counts = await test_db.get_vote_counts(poll_id)
    assert vote_counts[1] == 1


@pytest.mark.asyncio
async def test_close_poll(test_db, mock_bot, mock_llm_service):
    """Test closing a poll."""
    poll_manager = PollManager(mock_bot, test_db, mock_llm_service)

    chat_id = 12345
    poll_id = "test_poll"

    await test_db.save_poll(chat_id, poll_id, 1, ["a", "b", "c", "d"])
    await test_db.save_vote(poll_id, 123, 1)
    await test_db.save_vote(poll_id, 124, 1)
    await test_db.save_vote(poll_id, 125, 0)

    await poll_manager.close_poll(chat_id, poll_id)

    history = await test_db.get_chat_history(chat_id)
    assert len(history) == 1
    assert history[0]["winner_option"] == 1


@pytest.mark.asyncio
async def test_get_poll_status(test_db, mock_bot, mock_llm_service):
    """Test getting poll status."""
    poll_manager = PollManager(mock_bot, test_db, mock_llm_service)

    chat_id = 12345
    poll_id = "test_poll"

    await test_db.save_poll(chat_id, poll_id, 1, ["a", "b", "c", "d"])

    status = await poll_manager.get_poll_status(chat_id)
    assert status is not None
    assert status["poll_id"] == poll_id


@pytest.mark.asyncio
async def test_create_poll_with_active_poll(test_db, mock_bot, mock_llm_service):
    """Test creating poll when one already exists."""
    poll_manager = PollManager(mock_bot, test_db, mock_llm_service)

    chat_id = 12345
    await test_db.save_poll(chat_id, "existing_poll", 1, ["a", "b", "c", "d"])

    poll_id = await poll_manager.create_poll(chat_id)

    assert poll_id is None


@pytest.mark.asyncio
async def test_handle_poll_answer_empty_list(test_db, mock_bot, mock_llm_service):
    """Test handling poll answer with empty option list."""
    poll_manager = PollManager(mock_bot, test_db, mock_llm_service)

    poll_id = "test_poll"
    user_id = 123
    option_ids = []

    await poll_manager.handle_poll_answer(poll_id, user_id, option_ids)

    vote_counts = await test_db.get_vote_counts(poll_id)
    assert len(vote_counts) == 0


@pytest.mark.asyncio
async def test_close_poll_no_votes(test_db, mock_bot, mock_llm_service):
    """Test closing poll with no votes."""
    poll_manager = PollManager(mock_bot, test_db, mock_llm_service)

    chat_id = 12345
    poll_id = "test_poll"

    await test_db.save_poll(chat_id, poll_id, 1, ["a", "b", "c", "d"])

    await poll_manager.close_poll(chat_id, poll_id)

    history = await test_db.get_chat_history(chat_id)
    assert len(history) == 1
    assert history[0]["winner_option"] == 0


@pytest.mark.asyncio
async def test_get_poll_status_no_active_poll(test_db, mock_bot, mock_llm_service):
    """Test getting poll status when no active poll exists."""
    poll_manager = PollManager(mock_bot, test_db, mock_llm_service)

    chat_id = 12345

    status = await poll_manager.get_poll_status(chat_id)
    assert status is None


@pytest.mark.asyncio
async def test_get_active_polls_count(test_db, mock_bot, mock_llm_service):
    """Test getting active polls count."""
    poll_manager = PollManager(mock_bot, test_db, mock_llm_service)

    chat_id = 12345

    await poll_manager.create_poll(chat_id)

    count = poll_manager.get_active_polls_count()
    assert count == 1

    for task in poll_manager.active_polls.values():
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass


@pytest.mark.asyncio
async def test_create_poll_invalid_options_count(test_db, mock_bot, mock_llm_service):
    """Test creating poll when LLM returns invalid number of options."""
    poll_manager = PollManager(mock_bot, test_db, mock_llm_service)

    mock_llm_service.generate_code_options = AsyncMock(
        return_value=["option1", "option2", "option3"]
    )

    chat_id = 12345
    poll_id = await poll_manager.create_poll(chat_id)

    assert poll_id is None


@pytest.mark.asyncio
async def test_close_poll_creates_next_poll(test_db, mock_bot, mock_llm_service):
    """Test that closing a poll automatically creates the next one."""
    poll_manager = PollManager(mock_bot, test_db, mock_llm_service)

    chat_id = 12345
    poll_id = "test_poll"

    await test_db.save_poll(chat_id, poll_id, 1, ["a", "b", "c", "d"])
    await test_db.save_vote(poll_id, 123, 0)

    await poll_manager.close_poll(chat_id, poll_id)

    assert mock_bot.send_poll.called

    for task in poll_manager.active_polls.values():
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
