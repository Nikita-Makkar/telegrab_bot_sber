"""Bot command and message handlers."""

import logging
import os
import tempfile
from datetime import datetime
from typing import Optional, List

import aiofiles
from aiogram import Router, Bot
from aiogram.filters import Command
from aiogram.types import Message, PollAnswer, BufferedInputFile
from aiogram.fsm.context import FSMContext

from bot.config import Config
from bot.database import Database
from bot.poll_manager import PollManager
from bot.llm_service_unified import UnifiedLLMService
from bot.utils import build_code_from_history, escape_html, sanitize_error_message
from bot.constants import (
    MSG_START_NOT_ADMIN,
    MSG_START_INIT_ERROR,
    MSG_START_SUCCESS,
    MSG_START_NO_POLL,
    MSG_START_ERROR,
    MSG_CODE_INIT_ERROR,
    MSG_CODE_EMPTY,
    MSG_CODE_ERROR,
    MSG_CODE_COMPLETED_NOT_ADMIN,
    MSG_CODE_COMPLETED_INIT_ERROR,
    MSG_CODE_COMPLETED_EMPTY,
    MSG_CODE_COMPLETED_PROGRESS,
    MSG_CODE_COMPLETED_TRUNCATED,
    MSG_CODE_COMPLETED_FULL,
    MSG_CODE_COMPLETED_FILE_ERROR,
    MSG_CODE_COMPLETED_ERROR,
    MSG_SENDNOW_NOT_ADMIN,
    MSG_SENDNOW_INIT_ERROR,
    MSG_SENDNOW_ACTIVE_POLL,
    MSG_SENDNOW_SUCCESS,
    MSG_SENDNOW_ERROR,
    MSG_HEALTH_NOT_ADMIN,
    MSG_HEALTH_INIT_ERROR,
    MSG_HEALTH_STATUS,
    MSG_HEALTH_POLL_ACTIVE,
    MSG_HEALTH_POLL_ACTIVE_NO_TIMER,
    MSG_HEALTH_NO_POLL,
    MSG_LOGS_NOT_ADMIN,
    MSG_LOGS_FILE_NOT_FOUND,
    MSG_LOGS_ERROR,
    MSG_ALLLOGS_FILE_NOT_FOUND,
    MSG_POLL_MANAGER_MISSING,
)

logger = logging.getLogger(__name__)

router = Router()


def is_admin(user_id: int) -> bool:
    """Check if user is admin."""
    return user_id in Config.ADMIN_USER_IDS


@router.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext) -> None:
    """Handle /start command - admin only, clears history and sends first poll."""
    if not is_admin(message.from_user.id):
        await message.answer(MSG_START_NOT_ADMIN)
        return

    bot: Bot = message.bot
    poll_manager: Optional[PollManager] = getattr(bot, "poll_manager", None)
    database: Optional[Database] = getattr(bot, "database", None)

    if not poll_manager or not database:
        await message.answer(MSG_START_INIT_ERROR)
        return

    chat_id: int = message.chat.id

    try:
        await database.clear_chat_history(chat_id)
        logger.info(f"Admin {message.from_user.id} cleared history for chat {chat_id}")

        poll_id: Optional[str] = await poll_manager.create_poll(chat_id)
        if poll_id:
            await message.answer(MSG_START_SUCCESS)
        else:
            await message.answer(MSG_START_NO_POLL)
    except Exception as e:
        logger.error(f"Error in /start command: {e}", exc_info=True)
        await message.answer(MSG_START_ERROR.format(error=str(e)))


@router.message(Command("code"))
async def cmd_code(message: Message, state: FSMContext) -> None:
    """Handle /code command - show current code for the chat."""
    database: Optional[Database] = getattr(message.bot, "database", None)
    if not database:
        await message.answer(MSG_CODE_INIT_ERROR)
        return

    chat_id: int = message.chat.id

    try:
        history = await database.get_chat_history(chat_id)

        if not history:
            await message.answer(MSG_CODE_EMPTY)
            return

        code: str = build_code_from_history(history)
        response: str = f"<pre>{escape_html(code)}</pre>"
        await message.answer(response, parse_mode="HTML")

    except Exception as e:
        logger.error(f"Error in /code command: {e}", exc_info=True)
        await message.answer(MSG_CODE_ERROR.format(error=sanitize_error_message(e)))


@router.message(Command("code_completed"))
async def cmd_code_completed(message: Message, state: FSMContext) -> None:
    """Handle /code_completed command - complete code to be compilable (admin only)."""
    if not is_admin(message.from_user.id):
        await message.answer(MSG_CODE_COMPLETED_NOT_ADMIN)
        return

    database: Optional[Database] = getattr(message.bot, "database", None)
    llm_service: Optional[UnifiedLLMService] = getattr(message.bot, "llm_service", None)

    if not database or not llm_service:
        await message.answer(MSG_CODE_COMPLETED_INIT_ERROR)
        return

    chat_id: int = message.chat.id

    try:
        history = await database.get_chat_history(chat_id)

        if not history:
            await message.answer(MSG_CODE_COMPLETED_EMPTY)
            return

        current_code: str = build_code_from_history(history)
        await message.answer(MSG_CODE_COMPLETED_PROGRESS)

        completed_code: str = await llm_service.complete_code(current_code)
        completed_code_escaped: str = escape_html(completed_code)

        max_code_length: int = 3800

        if len(completed_code_escaped) > max_code_length:
            response_text: str = MSG_CODE_COMPLETED_TRUNCATED.format(
                code=completed_code_escaped[:max_code_length]
            )
        else:
            response_text = MSG_CODE_COMPLETED_FULL.format(code=completed_code_escaped)

        await message.answer(response_text, parse_mode="HTML")

        temp_path: Optional[str] = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".py", delete=False, encoding="utf-8"
            ) as f:
                f.write(completed_code)
                temp_path = f.name

            async with aiofiles.open(temp_path, "rb") as file:
                file_data = await file.read()
                input_file = BufferedInputFile(file_data, filename="completed_code.py")
                await message.answer_document(
                    input_file,
                    caption=f"Completed code - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                )
        except Exception as file_error:
            logger.error(f"Error sending file: {file_error}", exc_info=True)
            error_msg: str = sanitize_error_message(file_error, max_length=200)
            await message.answer(MSG_CODE_COMPLETED_FILE_ERROR.format(error=error_msg))
        finally:
            if temp_path and os.path.exists(temp_path):
                try:
                    os.unlink(temp_path)
                except Exception as cleanup_error:
                    logger.warning(f"Could not delete temp file {temp_path}: {cleanup_error}")

    except Exception as e:
        logger.error(f"Error in /code_completed command: {e}", exc_info=True)
        error_msg: str = sanitize_error_message(e)
        await message.answer(MSG_CODE_COMPLETED_ERROR.format(error=error_msg), parse_mode=None)


@router.message(Command("sendnow"))
async def cmd_sendnow(message: Message, state: FSMContext) -> None:
    """Handle /sendnow command - send next poll immediately (admin only)."""
    if not is_admin(message.from_user.id):
        await message.answer(MSG_SENDNOW_NOT_ADMIN)
        return

    poll_manager: Optional[PollManager] = getattr(message.bot, "poll_manager", None)
    database: Optional[Database] = getattr(message.bot, "database", None)

    if not poll_manager or not database:
        await message.answer(MSG_SENDNOW_INIT_ERROR)
        return

    chat_id: int = message.chat.id

    try:
        active = await database.get_active_poll(chat_id)
        if active:
            await message.answer(MSG_SENDNOW_ACTIVE_POLL.format(line_number=active["line_number"]))
            return

        poll_id: Optional[str] = await poll_manager.create_poll(chat_id)
        if poll_id:
            await message.answer(MSG_SENDNOW_SUCCESS)
        else:
            await message.answer(MSG_SENDNOW_ERROR)

    except Exception as e:
        logger.error(f"Error in /sendnow command: {e}", exc_info=True)
        await message.answer(MSG_START_ERROR.format(error=str(e)))


@router.message(Command("health"))
async def cmd_health(message: Message, state: FSMContext) -> None:
    """Handle /health command - show bot status (admin only)."""
    if not is_admin(message.from_user.id):
        await message.answer(MSG_HEALTH_NOT_ADMIN)
        return

    poll_manager: Optional[PollManager] = getattr(message.bot, "poll_manager", None)
    database: Optional[Database] = getattr(message.bot, "database", None)
    start_time: Optional[datetime] = getattr(message.bot, "start_time", None)

    if not poll_manager or not database or not start_time:
        await message.answer(MSG_HEALTH_INIT_ERROR)
        return

    try:
        uptime = datetime.now() - start_time
        uptime_str: str = (
            f"{uptime.days}d {uptime.seconds // 3600}h {(uptime.seconds % 3600) // 60}m"
        )

        active_polls_count: int = poll_manager.get_active_polls_count()
        chat_id: int = message.chat.id
        poll_status = await poll_manager.get_poll_status(chat_id)

        if poll_status:
            time_remaining: Optional[int] = poll_status.get("time_remaining_seconds")
            if time_remaining is not None:
                minutes: int = time_remaining // 60
                seconds: int = time_remaining % 60
                current_poll_line = MSG_HEALTH_POLL_ACTIVE.format(
                    line_number=poll_status["line_number"], minutes=minutes, seconds=seconds
                )
            else:
                current_poll_line = MSG_HEALTH_POLL_ACTIVE_NO_TIMER.format(
                    line_number=poll_status["line_number"]
                )
        else:
            current_poll_line = MSG_HEALTH_NO_POLL

        response = MSG_HEALTH_STATUS.format(
            uptime=uptime_str,
            active_polls_count=active_polls_count,
            current_poll_status=current_poll_line,
        )

        await message.answer(response)

    except Exception as e:
        logger.error(f"Error in /health command: {e}", exc_info=True)
        await message.answer(MSG_START_ERROR.format(error=str(e)))


@router.message(Command("logs"))
async def cmd_logs(message: Message) -> None:
    """Handle /logs command - show last ~100 lines of log (admin only)."""
    if not is_admin(message.from_user.id):
        await message.answer(MSG_LOGS_NOT_ADMIN)
        return

    try:
        log_file: str = Config.LOG_FILE
        if not os.path.exists(log_file):
            await message.answer(MSG_LOGS_FILE_NOT_FOUND)
            return

        with open(log_file, "r", encoding="utf-8") as f:
            lines: List[str] = f.readlines()

        last_lines: List[str] = lines[-100:] if len(lines) > 100 else lines
        log_content: str = "".join(last_lines)

        if len(log_content) > 4000:
            log_content = "..." + log_content[-4000:]

        await message.answer(f"<pre>{log_content}</pre>", parse_mode="HTML")

    except Exception as e:
        logger.error(f"Error in /logs command: {e}", exc_info=True)
        await message.answer(MSG_LOGS_ERROR.format(error=str(e)))


@router.message(Command("alllogs"))
async def cmd_alllogs(message: Message) -> None:
    """Handle /alllogs command - send entire log file (admin only)."""
    if not is_admin(message.from_user.id):
        await message.answer(MSG_LOGS_NOT_ADMIN)
        return

    try:
        log_file: str = Config.LOG_FILE
        if not os.path.exists(log_file):
            await message.answer(MSG_ALLLOGS_FILE_NOT_FOUND)
            return

        async with aiofiles.open(log_file, "rb") as f:
            file_data = await f.read()
            input_file = BufferedInputFile(file_data, filename="bot.log")
            await message.answer_document(
                input_file,
                caption=f"Complete log file - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            )

    except Exception as e:
        logger.error(f"Error in /alllogs command: {e}", exc_info=True)
        error_msg: str = sanitize_error_message(e)
        await message.answer(MSG_LOGS_ERROR.format(error=error_msg), parse_mode=None)


@router.poll_answer()
async def handle_poll_answer(poll_answer: PollAnswer) -> None:
    """Handle poll answer updates."""
    try:
        poll_manager: Optional[PollManager] = getattr(poll_answer.bot, "poll_manager", None)
        if not poll_manager:
            logger.error(MSG_POLL_MANAGER_MISSING)
            return

        poll_id: str = poll_answer.poll_id
        user_id: int = poll_answer.user.id
        option_ids: List[int] = poll_answer.option_ids

        await poll_manager.handle_poll_answer(poll_id, user_id, option_ids)
        logger.debug(f"Processed poll answer: poll={poll_id}, user={user_id}")

    except Exception as e:
        logger.error(f"Error handling poll answer: {e}", exc_info=True)
