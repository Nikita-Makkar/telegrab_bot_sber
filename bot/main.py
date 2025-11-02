"""Main bot entry point."""

import asyncio
import logging
import sys
from datetime import datetime
from logging.handlers import RotatingFileHandler

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from bot.config import Config
from bot.database import Database
from bot.handlers import router
from bot.llm_service_unified import UnifiedLLMService
from bot.poll_manager import PollManager

# Configure logging
logging.basicConfig(
    level=getattr(logging, Config.LOG_LEVEL.upper()),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        RotatingFileHandler(Config.LOG_FILE, maxBytes=10 * 1024 * 1024, backupCount=5),
        logging.StreamHandler(sys.stdout),
    ],
)

logger = logging.getLogger(__name__)


# Global start time for uptime tracking
START_TIME = datetime.now()


async def main() -> None:
    """Main entry point for the bot."""
    try:
        Config.validate()
        logger.info("Configuration validated")

        bot: Bot = Bot(
            token=Config.BOT_TOKEN,
            default=DefaultBotProperties(parse_mode=ParseMode.HTML),
        )
        dispatcher: Dispatcher = Dispatcher()

        database: Database = Database()
        await database.init()
        logger.info("Database initialized")

        llm_service: UnifiedLLMService = UnifiedLLMService()
        logger.info(f"LLM service initialized with provider: {llm_service.provider}")

        poll_manager: PollManager = PollManager(bot, database, llm_service)

        bot.poll_manager = poll_manager
        bot.database = database
        bot.llm_service = llm_service
        bot.start_time = START_TIME

        dispatcher.include_router(router)

        logger.info("Restoring active polls...")

        logger.info("Bot starting...")
        await dispatcher.start_polling(bot, allowed_updates=dispatcher.resolve_used_update_types())

    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot shutdown complete")
