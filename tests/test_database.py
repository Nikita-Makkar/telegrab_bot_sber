"""Tests for database module."""

import pytest


@pytest.mark.asyncio
async def test_database_init(test_db):
    """Test database initialization."""
    # Database should be initialized without errors
    assert test_db is not None


@pytest.mark.asyncio
async def test_save_and_get_poll(test_db):
    """Test saving and retrieving polls."""
    chat_id = 12345
    poll_id = "test_poll_1"
    line_number = 1
    options = ["option1", "option2", "option3", "option4"]

    # Save poll
    await test_db.save_poll(chat_id, poll_id, line_number, options)

    # Get active poll
    active = await test_db.get_active_poll(chat_id)
    assert active is not None
    assert active["poll_id"] == poll_id
    assert active["line_number"] == line_number
    assert active["options"] == options


@pytest.mark.asyncio
async def test_vote_saving(test_db):
    """Test saving votes."""
    poll_id = "test_poll_1"
    user_id = 123
    option_id = 2

    await test_db.save_vote(poll_id, user_id, option_id)

    vote_counts = await test_db.get_vote_counts(poll_id)
    assert vote_counts[option_id] == 1


@pytest.mark.asyncio
async def test_close_poll(test_db):
    """Test closing a poll."""
    chat_id = 12345
    poll_id = "test_poll_1"
    line_number = 1
    options = ["option1", "option2", "option3", "option4"]
    winner_option = 1

    # Save poll
    await test_db.save_poll(chat_id, poll_id, line_number, options)

    # Close poll
    await test_db.close_poll(poll_id, winner_option)

    # Check history
    history = await test_db.get_chat_history(chat_id)
    assert len(history) == 1
    assert history[0]["winner_option"] == winner_option


@pytest.mark.asyncio
async def test_get_next_line_number(test_db):
    """Test getting next line number."""
    chat_id = 12345

    # First line should be 1
    next_line = await test_db.get_next_line_number(chat_id)
    assert next_line == 1

    # Save a poll
    await test_db.save_poll(chat_id, "poll1", 1, ["a", "b", "c", "d"])
    await test_db.close_poll("poll1", 0)

    # Next line should be 2
    next_line = await test_db.get_next_line_number(chat_id)
    assert next_line == 2


@pytest.mark.asyncio
async def test_clear_chat_history(test_db):
    """Test clearing chat history."""
    chat_id = 12345

    # Save some polls
    await test_db.save_poll(chat_id, "poll1", 1, ["a", "b", "c", "d"])
    await test_db.close_poll("poll1", 0)
    await test_db.save_vote("poll1", 123, 0)

    # Clear history
    await test_db.clear_chat_history(chat_id)

    # Check history is empty
    history = await test_db.get_chat_history(chat_id)
    assert len(history) == 0
