"""Tests for utility functions."""

from bot.utils import build_code_from_history, escape_html, sanitize_error_message


def test_build_code_from_history_empty():
    """Test building code from empty history."""
    history = []
    code = build_code_from_history(history)
    assert code == ""


def test_build_code_from_history():
    """Test building code from history."""
    history = [
        {
            "poll_id": "poll1",
            "line_number": 1,
            "options": ["def func():", "class A:", "x = 1", "y = 2"],
            "winner_option": 0,
        },
        {
            "poll_id": "poll2",
            "line_number": 2,
            "options": ["    pass", "    return", "    raise", "    print"],
            "winner_option": 1,
        },
    ]
    code = build_code_from_history(history)
    assert code == "def func():\n    return"


def test_build_code_from_history_no_winner():
    """Test building code from history with no winner option."""
    history = [
        {
            "poll_id": "poll1",
            "line_number": 1,
            "options": ["def func():", "class A:", "x = 1", "y = 2"],
            "winner_option": None,
        }
    ]
    code = build_code_from_history(history)
    assert code == ""


def test_escape_html():
    """Test HTML escaping."""
    text = "Test & <test> \"quotes\" 'apostrophe'"
    escaped = escape_html(text)
    assert "&amp;" in escaped
    assert "&lt;" in escaped
    assert "&gt;" in escaped
    assert "&quot;" in escaped
    assert "&#x27;" in escaped


def test_escape_html_safe_text():
    """Test escaping safe text."""
    text = "Simple text without special characters"
    escaped = escape_html(text)
    assert escaped == text


def test_sanitize_error_message():
    """Test sanitizing error message."""
    error = ValueError("Test error message")
    sanitized = sanitize_error_message(error)
    assert isinstance(sanitized, str)
    assert "error" in sanitized.lower() or "test" in sanitized.lower()


def test_sanitize_error_message_long():
    """Test sanitizing long error message."""
    long_message = "x" * 1000
    error = ValueError(long_message)
    sanitized = sanitize_error_message(error, max_length=100)
    assert len(sanitized) <= 103
