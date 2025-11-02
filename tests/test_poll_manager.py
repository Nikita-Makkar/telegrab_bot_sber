"""Tests for poll manager."""

import asyncio
import pytest

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
    
    # Cleanup: cancel pending tasks to avoid warnings
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

    # First save poll
    await test_db.save_poll(12345, poll_id, 1, ["a", "b", "c", "d"])

    await poll_manager.handle_poll_answer(poll_id, user_id, option_ids)

    # Check vote was saved
    vote_counts = await test_db.get_vote_counts(poll_id)
    assert vote_counts[1] == 1


@pytest.mark.asyncio
async def test_close_poll(test_db, mock_bot, mock_llm_service):
    """Test closing a poll."""
    poll_manager = PollManager(mock_bot, test_db, mock_llm_service)

    chat_id = 12345
    poll_id = "test_poll"

    # Save poll with votes
    await test_db.save_poll(chat_id, poll_id, 1, ["a", "b", "c", "d"])
    await test_db.save_vote(poll_id, 123, 1)
    await test_db.save_vote(poll_id, 124, 1)
    await test_db.save_vote(poll_id, 125, 0)

    await poll_manager.close_poll(chat_id, poll_id)

    # Check poll is closed
    history = await test_db.get_chat_history(chat_id)
    assert len(history) == 1
    assert history[0]["winner_option"] == 1  # Option 1 has 2 votes


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
