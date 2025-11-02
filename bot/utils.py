"""Utility functions for the bot."""

from html import escape

from typing import List, Dict, Any

from bot.constants import ERROR_FORMAT_FAILED


def build_code_from_history(history: List[Dict[str, Any]]) -> str:
    """
    Build code string from chat history.

    Args:
        history: List of poll history items with winner_option

    Returns:
        Code string built from winning options
    """
    code_lines: List[str] = []
    for item in history:
        winner_option = item.get("winner_option")
        if winner_option is not None:
            options = item.get("options", [])
            if isinstance(options, list) and winner_option < len(options):
                winner_text = options[winner_option]
                code_lines.append(winner_text)
    return "\n".join(code_lines)


def escape_html(text: str) -> str:
    """Return an HTML‑escaped string."""
    return escape(text, quote=True)


def sanitize_error_message(error: Exception, max_length: int = 500) -> str:
    """
    Sanitize error message for safe display in Telegram.

    Args:
        error: Exception to format
        max_length: Maximum length of error message

    Returns:
        Sanitized error message
    """
    try:
        error_msg = str(error)
        error_msg = (
            error_msg.replace("_io.", "").replace("BufferedReader", "").replace("TextIOWrapper", "")
        )

        error_msg = (
            error_msg.replace("<", "")
            .replace(">", "")
            .replace("&", "&amp;")
            .replace('"', "&quot;")
            .replace("'", "&#x27;")
        )

        if len(error_msg) > max_length:
            error_msg = error_msg[:max_length] + "..."

        return error_msg
    except Exception:
        return ERROR_FORMAT_FAILED
