"""
Унифицированный LLM сервис с автоматическим выбором провайдера.

Использует Groq по умолчанию, но может переключиться на OpenAI.
"""

import logging
import json
from typing import List, Optional, Dict, Any

from bot.config import Config
from bot.constants import (
    ERROR_COMPLETING_CODE,
    ERROR_GENERATING_OPTIONS,
    ERROR_GROQ_KEY_NOT_FOUND,
    ERROR_NO_LLM_KEY,
    ERROR_OPENAI_KEY_NOT_FOUND,
    ERROR_UNKNOWN_PROVIDER,
    FALLBACK_CODE_OPTIONS,
    MSG_GROQ_AUTO_SELECTION,
    MSG_GROQ_INITIALIZED,
    MSG_OPENAI_AUTO_SELECTION,
    MSG_OPENAI_INITIALIZED,
    PROMPT_CODE_COMPLETION,
    PROMPT_CODE_GENERATION,
    DEFAULT_CODE_CONTEXT,
    DEFAULT_LANGUAGE,
    GROQ_API_BASE_URL,
    DEFAULT_GROQ_MODEL,
    DEFAULT_OPENAI_MODEL,
)


logger = logging.getLogger(__name__)


class UnifiedLLMService:
    """Унифицированный LLM сервис с поддержкой Groq и OpenAI."""

    def __init__(self, provider: Optional[str] = None) -> None:
        """
        Инициализация LLM сервиса с автоматическим выбором провайдера.

        Args:
            provider: "groq", "openai" или None для автовыбора.
        """
        if provider:
            self.provider = provider.lower()
        elif Config.LLM_PROVIDER:
            self.provider = Config.LLM_PROVIDER.lower()
        else:
            # Автоматический выбор провайдера
            if Config.GROQ_API_KEY:
                self.provider = "groq"
                logger.info(MSG_GROQ_AUTO_SELECTION)
            elif Config.OPENAI_API_KEY:
                self.provider = "openai"
                logger.info(MSG_OPENAI_AUTO_SELECTION)
            else:
                raise ValueError(ERROR_NO_LLM_KEY)

        self._init_client()

    def _init_client(self) -> None:
        """Инициализация клиента для выбранного провайдера."""
        from openai import AsyncOpenAI

        if self.provider == "groq":
            if not Config.GROQ_API_KEY:
                raise ValueError(ERROR_GROQ_KEY_NOT_FOUND)

            self.client = AsyncOpenAI(
                api_key=Config.GROQ_API_KEY,
                base_url=GROQ_API_BASE_URL,
            )
            self.model = getattr(Config, "GROQ_MODEL", DEFAULT_GROQ_MODEL)
            logger.info(MSG_GROQ_INITIALIZED.format(model=self.model))

        elif self.provider == "openai":
            if not Config.OPENAI_API_KEY:
                raise ValueError(ERROR_OPENAI_KEY_NOT_FOUND)

            self.client = AsyncOpenAI(api_key=Config.OPENAI_API_KEY)
            self.model = getattr(Config, "OPENAI_MODEL", DEFAULT_OPENAI_MODEL)
            logger.info(MSG_OPENAI_INITIALIZED.format(model=self.model))

        else:
            raise ValueError(ERROR_UNKNOWN_PROVIDER.format(provider=self.provider))

    async def generate_code_options(
        self, chat_history: List[Dict[str, Any]], max_length: int = 95
    ) -> List[str]:
        """
        Генерирует 4 синтаксически корректные строки кода на основе истории.

        Args:
            chat_history: история чата с предыдущими вариантами
            max_length: максимальная длина строки

        Returns:
            Список из 4 строк кода
        """
        from bot.utils import build_code_from_history

        code_context = build_code_from_history(chat_history)
        context = code_context if code_context else DEFAULT_CODE_CONTEXT

        prompt = PROMPT_CODE_GENERATION.format(max_length=max_length, code_context=context)

        try:
            return await self._generate_with_api(prompt, max_length)
        except Exception as e:
            logger.error(ERROR_GENERATING_OPTIONS.format(provider=self.provider, error=e))
            return self._fallback_options(context)

    async def _generate_with_api(self, prompt: str, max_length: int) -> List[str]:
        """Генерация вариантов кода через OpenAI-совместимый API."""
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            temperature=0.8,
        )

        content = response.choices[0].message.content

        try:
            parsed = json.loads(content)
            options = parsed.get("options", [])
        except json.JSONDecodeError:
            logger.warning("Некорректный JSON-ответ от модели.")
            return self._fallback_options("")

        if len(options) != 4:
            logger.warning("Модель вернула некорректное количество опций.")
            return self._fallback_options("")

        options = [str(opt)[:max_length] for opt in options]

        while len(options) < 4:
            options.extend(self._fallback_options("")[: 4 - len(options)])

        return options[:4]

    def _fallback_options(self, code_context: str) -> List[str]:
        """Возвращает запасные варианты, если генерация не удалась."""
        return FALLBACK_CODE_OPTIONS[:4]

    async def complete_code(self, code: str, language: str = DEFAULT_LANGUAGE) -> str:
        """
        Завершает код до компилируемого состояния без добавления новой логики.

        Args:
            code: исходный код
            language: язык программирования

        Returns:
            Завершённая версия кода
        """
        prompt = PROMPT_CODE_COMPLETION.format(language=language, code=code)

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2,
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            logger.error(ERROR_COMPLETING_CODE.format(provider=self.provider, error=e))
            return code
