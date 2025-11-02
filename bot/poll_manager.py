"""Poll management system."""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, Optional, List, Any
import logging

from aiogram import Bot

from bot.config import Config
from bot.database import Database
from bot.llm_service_unified import UnifiedLLMService

logger = logging.getLogger(__name__)


class PollManager:
    """Manages polls lifecycle and voting."""

    def __init__(self, bot: Bot, database: Database, llm_service: UnifiedLLMService) -> None:
        """Initialize poll manager."""
        self.bot: Bot = bot
        self.db: Database = database
        self.llm: UnifiedLLMService = llm_service
        self.active_polls: Dict[str, asyncio.Task] = {}
        self.poll_timers: Dict[str, datetime] = {}

    async def create_poll(self, chat_id: int) -> Optional[str]:
        """
        Create and send a new poll for the chat.

        Returns:
            poll_id if successful, None otherwise
        """
        try:
            # Get chat history
            history = await self.db.get_chat_history(chat_id)

            # Check if there's an active poll
            active = await self.db.get_active_poll(chat_id)
            if active:
                logger.info(f"Chat {chat_id} already has active poll {active['poll_id']}")
                return None

            # Get next line number
            line_number = await self.db.get_next_line_number(chat_id)

            # Generate options
            options = await self.llm.generate_code_options(
                history, max_length=Config.MAX_CODE_LINE_LENGTH
            )

            if len(options) != 4:
                logger.error(f"Failed to generate 4 options, got {len(options)}")
                return None

            # Create poll
            poll_message = await self.bot.send_poll(
                chat_id=chat_id,
                question=f"Line {line_number}: Choose the next code line",
                options=options,
                is_anonymous=False,
                allows_multiple_answers=False,
            )

            poll_id = poll_message.poll.id
            message_id = poll_message.message_id

            # Save poll to database
            await self.db.save_poll(chat_id, poll_id, line_number, options, message_id)

            # Schedule poll closure
            close_time = datetime.now() + timedelta(seconds=Config.POLL_DURATION_SECONDS)
            self.poll_timers[poll_id] = close_time
            task = asyncio.create_task(self._close_poll_after_duration(chat_id, poll_id))
            self.active_polls[poll_id] = task

            logger.info(
                f"Created poll {poll_id} for chat {chat_id}, line {line_number}, "
                f"closes at {close_time}"
            )
            return poll_id

        except Exception as e:
            logger.error(f"Error creating poll for chat {chat_id}: {e}", exc_info=True)
            return None

    async def _close_poll_after_duration(self, chat_id: int, poll_id: str) -> None:
        """Close poll after duration expires."""
        try:
            await asyncio.sleep(Config.POLL_DURATION_SECONDS)
            await self.close_poll(chat_id, poll_id)
        except asyncio.CancelledError:
            logger.info(f"Poll {poll_id} close task cancelled")
        except Exception as e:
            logger.error(f"Error closing poll {poll_id} after duration: {e}", exc_info=True)

    async def handle_poll_answer(self, poll_id: str, user_id: int, option_ids: List[int]) -> None:
        """Handle a poll answer update."""
        if not option_ids:
            return

        option_id: int = option_ids[0]

        try:
            await self.db.save_vote(poll_id, user_id, option_id)
            logger.debug(f"Saved vote: poll {poll_id}, user {user_id}, option {option_id}")
        except Exception as e:
            logger.error(f"Error saving vote: {e}", exc_info=True)

    async def close_poll(self, chat_id: int, poll_id: str) -> None:
        """
        Close a poll and determine the winner.

        Args:
            chat_id: Chat ID
            poll_id: Poll ID to close
        """
        try:

            if poll_id in self.active_polls:
                task = self.active_polls.pop(poll_id)
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass

            active = await self.db.get_active_poll(chat_id)
            message_id = (
                active.get("message_id") if active and active.get("poll_id") == poll_id else None
            )

            vote_counts: Dict[int, int] = await self.db.get_vote_counts(poll_id)

            if not vote_counts:
                logger.warning(f"No votes for poll {poll_id}, using first option as default")
                winner_option: int = 0
            else:
                winner_option = max(vote_counts.items(), key=lambda x: x[1])[0]

            await self.db.close_poll(poll_id, winner_option)

            if message_id:
                try:
                    await self.bot.stop_poll(chat_id=chat_id, message_id=message_id)
                except Exception as e:
                    logger.debug(f"Could not stop poll via API: {e}")

            if poll_id in self.poll_timers:
                del self.poll_timers[poll_id]

            logger.info(f"Closed poll {poll_id}, winner: option {winner_option}")

            await asyncio.sleep(1)
            await self.create_poll(chat_id)

        except Exception as e:
            logger.error(f"Error closing poll {poll_id}: {e}", exc_info=True)

    async def get_poll_status(self, chat_id: int) -> Optional[Dict[str, Any]]:
        """Get status of active poll for a chat."""
        active: Optional[Dict[str, Any]] = await self.db.get_active_poll(chat_id)
        if not active:
            return None

        poll_id: str = active["poll_id"]
        close_time: Optional[datetime] = self.poll_timers.get(poll_id)
        if close_time:
            time_remaining: float = (close_time - datetime.now()).total_seconds()
            active["time_remaining_seconds"] = max(0, int(time_remaining))
        else:
            active["time_remaining_seconds"] = None

        return active

    def get_active_polls_count(self) -> int:
        """Get count of active polls."""
        return len(self.active_polls)
