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


async def main():
    """Main entry point for the bot."""
    try:
        # Validate configuration
        Config.validate()
        logger.info("Configuration validated")

        # Initialize components
        bot = Bot(
            token=Config.BOT_TOKEN,
            default=DefaultBotProperties(parse_mode=ParseMode.HTML),
        )
        dispatcher = Dispatcher()

        database = Database()
        await database.init()
        logger.info("Database initialized")

        # Инициализация LLM сервиса с автоматическим выбором провайдера
        # По умолчанию использует Groq, если доступен GROQ_API_KEY
        # Можно переопределить через LLM_PROVIDER в .env
        llm_service = UnifiedLLMService()
        logger.info(f"LLM service initialized with provider: {llm_service.provider}")

        poll_manager = PollManager(bot, database, llm_service)

        # Store dependencies as bot attributes for handlers to access
        bot.poll_manager = poll_manager
        bot.database = database
        bot.llm_service = llm_service
        bot.start_time = START_TIME

        # Register handlers
        dispatcher.include_router(router)

        # Restore active polls from database
        logger.info("Restoring active polls...")
        # Note: This is simplified - in production you'd want to restore timer tasks
        # For now, polls will just be tracked in DB and closed when they expire

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
