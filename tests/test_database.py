"""Tests for database module."""

import pytest


@pytest.mark.asyncio
async def test_database_init(test_db):
    """Test database initialization."""
    assert test_db is not None


@pytest.mark.asyncio
async def test_save_and_get_poll(test_db):
    """Test saving and retrieving polls."""
    chat_id = 12345
    poll_id = "test_poll_1"
    line_number = 1
    options = ["option1", "option2", "option3", "option4"]

    await test_db.save_poll(chat_id, poll_id, line_number, options)

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

    await test_db.save_poll(chat_id, poll_id, line_number, options)

    await test_db.close_poll(poll_id, winner_option)

    history = await test_db.get_chat_history(chat_id)
    assert len(history) == 1
    assert history[0]["winner_option"] == winner_option


@pytest.mark.asyncio
async def test_get_next_line_number(test_db):
    """Test getting next line number."""
    chat_id = 12345

    next_line = await test_db.get_next_line_number(chat_id)
    assert next_line == 1

    await test_db.save_poll(chat_id, "poll1", 1, ["a", "b", "c", "d"])
    await test_db.close_poll("poll1", 0)

    next_line = await test_db.get_next_line_number(chat_id)
    assert next_line == 2


@pytest.mark.asyncio
async def test_clear_chat_history(test_db):
    """Test clearing chat history."""
    chat_id = 12345

    await test_db.save_poll(chat_id, "poll1", 1, ["a", "b", "c", "d"])
    await test_db.close_poll("poll1", 0)
    await test_db.save_vote("poll1", 123, 0)

    await test_db.clear_chat_history(chat_id)

    history = await test_db.get_chat_history(chat_id)
    assert len(history) == 0


@pytest.mark.asyncio
async def test_get_chat_history_empty(test_db):
    """Test getting chat history for empty chat."""
    chat_id = 99999
    history = await test_db.get_chat_history(chat_id)
    assert len(history) == 0


@pytest.mark.asyncio
async def test_get_active_poll_none(test_db):
    """Test getting active poll when none exists."""
    chat_id = 99999
    active = await test_db.get_active_poll(chat_id)
    assert active is None


@pytest.mark.asyncio
async def test_get_vote_counts_empty(test_db):
    """Test getting vote counts for poll with no votes."""
    poll_id = "no_votes_poll"
    vote_counts = await test_db.get_vote_counts(poll_id)
    assert len(vote_counts) == 0


@pytest.mark.asyncio
async def test_multiple_votes_same_option(test_db):
    """Test multiple users voting for same option."""
    poll_id = "test_poll"
    option_id = 2

    await test_db.save_vote(poll_id, 1, option_id)
    await test_db.save_vote(poll_id, 2, option_id)
    await test_db.save_vote(poll_id, 3, option_id)

    vote_counts = await test_db.get_vote_counts(poll_id)
    assert vote_counts[option_id] == 3


@pytest.mark.asyncio
async def test_multiple_votes_different_options(test_db):
    """Test multiple users voting for different options."""
    poll_id = "test_poll"

    await test_db.save_vote(poll_id, 1, 0)
    await test_db.save_vote(poll_id, 2, 1)
    await test_db.save_vote(poll_id, 3, 2)

    vote_counts = await test_db.get_vote_counts(poll_id)
    assert vote_counts[0] == 1
    assert vote_counts[1] == 1
    assert vote_counts[2] == 1


@pytest.mark.asyncio
async def test_update_vote_same_user(test_db):
    """Test updating vote by same user."""
    poll_id = "test_poll"
    user_id = 123

    await test_db.save_vote(poll_id, user_id, 0)
    vote_counts = await test_db.get_vote_counts(poll_id)
    assert vote_counts[0] == 1

    await test_db.save_vote(poll_id, user_id, 1)
    vote_counts = await test_db.get_vote_counts(poll_id)
    # Option 0 should not be in results since no votes for it
    assert 0 not in vote_counts
    assert vote_counts[1] == 1
