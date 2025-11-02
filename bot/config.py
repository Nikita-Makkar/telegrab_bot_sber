"""Configuration management for the bot."""

import os
from typing import List

from dotenv import load_dotenv

load_dotenv()


class Config:
    """Bot configuration from environment variables."""

    # Telegram
    BOT_TOKEN: str = os.getenv("BOT_TOKEN", "")
    ADMIN_USER_IDS: List[int] = [
        int(uid.strip()) for uid in os.getenv("ADMIN_USER_IDS", "").split(",") if uid.strip()
    ]

    # OpenAI
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

    # Groq API (бесплатный)
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")

    # Hugging Face API (бесплатный tier)
    HUGGINGFACE_API_KEY: str = os.getenv("HUGGINGFACE_API_KEY", "")

    # Ollama (локальный, бесплатный)
    OLLAMA_BASE_URL: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    OLLAMA_MODEL: str = os.getenv("OLLAMA_MODEL", "llama3.2")

    # LLM Provider selection (groq, openai, huggingface, ollama)
    # Если не указан, автоматически выберет доступный провайдер
    LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "").lower()

    # Bot Settings
    POLL_DURATION_SECONDS: int = int(os.getenv("POLL_DURATION_SECONDS", "300"))
    MAX_CODE_LINE_LENGTH: int = int(os.getenv("MAX_CODE_LINE_LENGTH", "95"))

    # Database
    DATABASE_PATH: str = os.getenv("DATABASE_PATH", "bot_data.db")

    # Logging
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    LOG_FILE: str = os.getenv("LOG_FILE", "bot.log")

    @classmethod
    def validate(cls) -> None:
        """Validate that required configuration is present."""
        if not cls.BOT_TOKEN:
            raise ValueError("BOT_TOKEN is required")

        # Если провайдер явно указан, проверяем соответствующий ключ
        if cls.LLM_PROVIDER:
            if cls.LLM_PROVIDER == "groq" and not cls.GROQ_API_KEY:
                raise ValueError("GROQ_API_KEY is required when LLM_PROVIDER=groq")
            elif cls.LLM_PROVIDER == "openai" and not cls.OPENAI_API_KEY:
                raise ValueError("OPENAI_API_KEY is required when LLM_PROVIDER=openai")
            elif cls.LLM_PROVIDER == "huggingface" and not cls.HUGGINGFACE_API_KEY:
                raise ValueError("HUGGINGFACE_API_KEY is required when LLM_PROVIDER=huggingface")
        else:
            # Проверяем наличие хотя бы одного LLM ключа для автовыбора
            has_llm = cls.OPENAI_API_KEY or cls.GROQ_API_KEY or cls.HUGGINGFACE_API_KEY
            if not has_llm:
                raise ValueError(
                    "At least one LLM API key is required: "
                    "OPENAI_API_KEY, GROQ_API_KEY, or HUGGINGFACE_API_KEY"
                )

        if not cls.ADMIN_USER_IDS:
            raise ValueError("ADMIN_USER_IDS is required")
