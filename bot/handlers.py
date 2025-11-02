"""Bot command and message handlers."""

import logging
import os
import tempfile
from datetime import datetime

import aiofiles
from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message, PollAnswer, BufferedInputFile
from aiogram.fsm.context import FSMContext

from bot.config import Config

logger = logging.getLogger(__name__)

router = Router()


def is_admin(user_id: int) -> bool:
    """Check if user is admin."""
    return user_id in Config.ADMIN_USER_IDS


@router.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext):
    """Handle /start command - admin only, clears history and sends first poll."""
    if not is_admin(message.from_user.id):
        await message.answer("❌ This command is only available to administrators.")
        return

    bot = message.bot
    poll_manager = getattr(bot, "poll_manager", None)
    database = getattr(bot, "database", None)

    if not poll_manager or not database:
        await message.answer("❌ Bot not properly initialized.")
        return

    chat_id = message.chat.id

    try:
        # Clear chat history
        await database.clear_chat_history(chat_id)
        logger.info(f"Admin {message.from_user.id} cleared history for chat {chat_id}")

        # Create first poll
        poll_id = await poll_manager.create_poll(chat_id)
        if poll_id:
            await message.answer(
                "✅ Chat history cleared. First poll created!\n"
                "The bot will automatically create new polls after each closes."
            )
        else:
            await message.answer(
                "✅ Chat history cleared.\n"
                "⚠️ Failed to create poll. Try /sendnow to send manually."
            )
    except Exception as e:
        logger.error(f"Error in /start command: {e}", exc_info=True)
        await message.answer(f"❌ Error: {str(e)}")


@router.message(Command("code"))
async def cmd_code(message: Message, state: FSMContext):
    """Handle /code command - show current code for the chat."""
    database = getattr(message.bot, "database", None)
    if not database:
        await message.answer("❌ Bot not properly initialized.")
        return

    chat_id = message.chat.id

    try:
        history = await database.get_chat_history(chat_id)

        if not history:
            await message.answer("📝 No code generated yet.\nUse /start to begin generating code.")
            return

        # Build code from winners
        code_lines = []
        for item in history:
            if item.get("winner_option") is not None:
                winner_text = item["options"][item["winner_option"]]
                code_lines.append(winner_text)

        code = "\n".join(code_lines)

        # Format as markdown code block
        response = f"<pre>{code}</pre>"

        await message.answer(response, parse_mode="HTML")

    except Exception as e:
        logger.error(f"Error in /code command: {e}", exc_info=True)
        await message.answer(f"❌ Error retrieving code: {str(e)}")


@router.message(Command("code_completed"))
async def cmd_code_completed(message: Message, state: FSMContext):
    """Handle /code_completed command - complete code to be compilable (admin only)."""
    if not is_admin(message.from_user.id):
        await message.answer("❌ This command is only available to administrators.")
        return

    database = getattr(message.bot, "database", None)
    llm_service = getattr(message.bot, "llm_service", None)

    if not database or not llm_service:
        await message.answer("❌ Bot not properly initialized.")
        return

    chat_id = message.chat.id

    try:
        history = await database.get_chat_history(chat_id)

        if not history:
            await message.answer("📝 No code to complete yet.")
            return

        # Build current code
        code_lines = []
        for item in history:
            if item.get("winner_option") is not None:
                winner_text = item["options"][item["winner_option"]]
                code_lines.append(winner_text)

        current_code = "\n".join(code_lines)

        # Complete code via LLM
        await message.answer("⏳ Completing code... This may take a moment.")
        completed_code = await llm_service.complete_code(current_code)

        # Escape HTML special characters properly
        def escape_html(text: str) -> str:
            """Safely escape HTML characters."""
            return (
                text.replace("&", "&amp;")
                .replace("<", "&lt;")
                .replace(">", "&gt;")
                .replace('"', "&quot;")
                .replace("'", "&#x27;")
            )

        completed_code_escaped = escape_html(completed_code)

        # Send as text (ограничиваем длину для Telegram)
        # Telegram limit is 4096 characters, оставляем запас
        max_code_length = 3800  # Оставляем место для префикса

        if len(completed_code_escaped) > max_code_length:
            # Отправляем только начало с предупреждением
            response_text = (
                "Completed code (truncated, full file will be sent as attachment):\n"
                f'<pre><code class="language-python">'
                f"{completed_code_escaped[:max_code_length]}...</code></pre>"
            )
        else:
            response_text = (
                "Completed code:\n"
                f'<pre><code class="language-python">{completed_code_escaped}</code></pre>'
            )

        await message.answer(response_text, parse_mode="HTML")

        # Send as file
        temp_path = None
        try:
            # Создаем временный файл
            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".py", delete=False, encoding="utf-8"
            ) as f:
                f.write(completed_code)
                temp_path = f.name

            # Читаем файл асинхронно и отправляем
            async with aiofiles.open(temp_path, "rb") as file:
                file_data = await file.read()

                input_file = BufferedInputFile(file_data, filename="completed_code.py")

                await message.answer_document(
                    input_file,
                    caption=f"Completed code - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                )
        except Exception as file_error:
            logger.error(f"Error sending file: {file_error}", exc_info=True)
            # Безопасное форматирование ошибки файла
            try:
                error_str = str(file_error)
                # Удаляем файловые объекты из строки
                error_str = (
                    error_str.replace("_io.", "")
                    .replace("BufferedReader", "")
                    .replace("TextIOWrapper", "")
                )
                error_str = error_str[:200] if len(error_str) > 200 else error_str
                await message.answer(
                    f"✅ Code completed, but error sending file: {error_str}", parse_mode=None
                )
            except Exception:
                await message.answer(
                    "✅ Code completed, but error sending file. Check logs for details.",
                    parse_mode=None,
                )
        finally:
            # Удаляем временный файл
            if temp_path and os.path.exists(temp_path):
                try:
                    os.unlink(temp_path)
                except Exception as cleanup_error:
                    logger.warning(f"Could not delete temp file {temp_path}: {cleanup_error}")

    except Exception as e:
        logger.error(f"Error in /code_completed command: {e}", exc_info=True)
        # Безопасное форматирование ошибки для Telegram
        # Преобразуем в строку безопасным способом
        try:
            error_msg = str(e)
            # Удаляем все объекты и файловые дескрипторы из строки
            error_msg = (
                error_msg.replace("_io.", "")
                .replace("BufferedReader", "")
                .replace("TextIOWrapper", "")
            )

            # Убираем проблемные символы для HTML
            error_msg = (
                error_msg.replace("<", "")
                .replace(">", "")
                .replace("&", "&amp;")
                .replace('"', "&quot;")
                .replace("'", "&#x27;")
            )

            # Ограничиваем длину
            if len(error_msg) > 500:
                error_msg = error_msg[:500] + "..."

            # Используем простой текст без HTML parse_mode для ошибок
            await message.answer(f"❌ Error completing code:\n{error_msg}", parse_mode=None)
        except Exception as safe_error:
            # Если даже форматирование ошибки не работает, отправляем общее сообщение
            logger.error(f"Error formatting error message: {safe_error}", exc_info=True)
            await message.answer(
                "❌ Error completing code. Check bot logs for details.", parse_mode=None
            )


@router.message(Command("sendnow"))
async def cmd_sendnow(message: Message, state: FSMContext):
    """Handle /sendnow command - send next poll immediately (admin only)."""
    if not is_admin(message.from_user.id):
        await message.answer("❌ This command is only available to administrators.")
        return

    poll_manager = getattr(message.bot, "poll_manager", None)
    database = getattr(message.bot, "database", None)

    if not poll_manager or not database:
        await message.answer("❌ Bot not properly initialized.")
        return

    chat_id = message.chat.id

    try:
        # Check if there's an active poll
        active = await database.get_active_poll(chat_id)
        if active:
            await message.answer(
                f"⚠️ There is already an active poll (Line {active['line_number']}).\n"
                f"Close it first or wait for it to expire."
            )
            return

        # Create new poll
        poll_id = await poll_manager.create_poll(chat_id)
        if poll_id:
            await message.answer("✅ New poll created and sent!")
        else:
            await message.answer("❌ Failed to create poll. Check logs for details.")

    except Exception as e:
        logger.error(f"Error in /sendnow command: {e}", exc_info=True)
        await message.answer(f"❌ Error: {str(e)}")


@router.message(Command("health"))
async def cmd_health(message: Message, state: FSMContext):
    """Handle /health command - show bot status (admin only)."""
    if not is_admin(message.from_user.id):
        await message.answer("❌ This command is only available to administrators.")
        return

    poll_manager = getattr(message.bot, "poll_manager", None)
    database = getattr(message.bot, "database", None)
    start_time = getattr(message.bot, "start_time", None)

    if not poll_manager or not database or not start_time:
        await message.answer("❌ Bot not properly initialized.")
        return

    try:
        uptime = datetime.now() - start_time
        uptime_str = f"{uptime.days}d {uptime.seconds // 3600}h {(uptime.seconds % 3600) // 60}m"

        active_polls_count = poll_manager.get_active_polls_count()

        chat_id = message.chat.id
        poll_status = await poll_manager.get_poll_status(chat_id)

        response_lines = [
            "🤖 Bot Health Status",
            "",
            f"⏱️ Uptime: {uptime_str}",
            f"📊 Active polls: {active_polls_count}",
        ]

        if poll_status:
            time_remaining = poll_status.get("time_remaining_seconds")
            if time_remaining is not None:
                minutes = time_remaining // 60
                seconds = time_remaining % 60
                response_lines.append(
                    f"📝 Current poll: Line {poll_status['line_number']}, "
                    f"closes in {minutes}m {seconds}s"
                )
            else:
                response_lines.append(f"📝 Current poll: Line {poll_status['line_number']}")
        else:
            response_lines.append("📝 No active poll in this chat")

        await message.answer("\n".join(response_lines))

    except Exception as e:
        logger.error(f"Error in /health command: {e}", exc_info=True)
        await message.answer(f"❌ Error: {str(e)}")


@router.message(Command("logs"))
async def cmd_logs(message: Message):
    """Handle /logs command - show last ~100 lines of log (admin only)."""
    if not is_admin(message.from_user.id):
        await message.answer("❌ This command is only available to administrators.")
        return

    try:
        log_file = Config.LOG_FILE
        if not os.path.exists(log_file):
            await message.answer("📄 No log file found.")
            return

        with open(log_file, "r", encoding="utf-8") as f:
            lines = f.readlines()

        # Get last ~100 lines
        last_lines = lines[-100:] if len(lines) > 100 else lines
        log_content = "".join(last_lines)

        # Telegram message limit is 4096 characters
        if len(log_content) > 4000:
            log_content = "..." + log_content[-4000:]

        await message.answer(f"<pre>{log_content}</pre>", parse_mode="HTML")

    except Exception as e:
        logger.error(f"Error in /logs command: {e}", exc_info=True)
        await message.answer(f"❌ Error: {str(e)}")


@router.message(Command("alllogs"))
async def cmd_alllogs(message: Message):
    """Handle /alllogs command - send entire log file (admin only)."""
    if not is_admin(message.from_user.id):
        await message.answer("❌ This command is only available to administrators.")
        return

    try:
        log_file = Config.LOG_FILE
        if not os.path.exists(log_file):
            await message.answer("📄 No log file found.")
            return

        with open(log_file, "rb") as f:
            await message.answer_document(
                f, caption=f"Complete log file - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            )

    except Exception as e:
        logger.error(f"Error in /alllogs command: {e}", exc_info=True)
        await message.answer(f"❌ Error: {str(e)}")


@router.poll_answer()
async def handle_poll_answer(poll_answer: PollAnswer):
    """Handle poll answer updates."""
    try:
        poll_manager = getattr(poll_answer.bot, "poll_manager", None)
        if not poll_manager:
            logger.error("PollManager not available")
            return

        poll_id = poll_answer.poll_id
        user_id = poll_answer.user.id
        option_ids = poll_answer.option_ids

        await poll_manager.handle_poll_answer(poll_id, user_id, option_ids)
        logger.debug(f"Processed poll answer: poll={poll_id}, user={user_id}")

    except Exception as e:
        logger.error(f"Error handling poll answer: {e}", exc_info=True)
