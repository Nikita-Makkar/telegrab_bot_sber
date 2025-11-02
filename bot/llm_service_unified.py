"""
Унифицированный LLM сервис с автоматическим выбором провайдера.

Использует Groq по умолчанию, но может переключиться на OpenAI.
"""

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
)


class UnifiedLLMService:
    """Унифицированный LLM сервис с поддержкой Groq и OpenAI."""

    def __init__(self, provider: Optional[str] = None) -> None:
        """
        Инициализация LLM сервиса с автоматическим выбором провайдера.

        Args:
            provider: "groq", "openai" или None для автовыбора
        """
        # Определяем провайдера
        if provider:
            self.provider: str = provider.lower()
        elif Config.LLM_PROVIDER:
            self.provider = Config.LLM_PROVIDER.lower()
        else:
            # Автоматический выбор: приоритет Groq -> OpenAI
            if Config.GROQ_API_KEY:
                self.provider = "groq"
                print(MSG_GROQ_AUTO_SELECTION)
            elif Config.OPENAI_API_KEY:
                self.provider = "openai"
                print(MSG_OPENAI_AUTO_SELECTION)
            else:
                raise ValueError(ERROR_NO_LLM_KEY)

        self._init_client()

    def _init_client(self) -> None:
        """Инициализация клиента для выбранного провайдера."""
        if self.provider == "groq":
            from openai import AsyncOpenAI

            if not Config.GROQ_API_KEY:
                raise ValueError(ERROR_GROQ_KEY_NOT_FOUND)

            self.client = AsyncOpenAI(
                api_key=Config.GROQ_API_KEY, base_url="https://api.groq.com/openai/v1"
            )
            self.model = "llama-3.1-8b-instant"
            print(MSG_GROQ_INITIALIZED.format(model=self.model))

        elif self.provider == "openai":
            from openai import AsyncOpenAI

            if not Config.OPENAI_API_KEY:
                raise ValueError(ERROR_OPENAI_KEY_NOT_FOUND)

            self.client = AsyncOpenAI(api_key=Config.OPENAI_API_KEY)
            self.model = Config.OPENAI_MODEL
            print(MSG_OPENAI_INITIALIZED.format(model=self.model))

        else:
            raise ValueError(ERROR_UNKNOWN_PROVIDER.format(provider=self.provider))

    async def generate_code_options(
        self, chat_history: List[Dict[str, Any]], max_length: int = 95
    ) -> List[str]:
        """
        Generate 4 syntactically correct code line options based on chat history.

        Args:
            chat_history: List of previous poll results with winner_option
            max_length: Maximum length for each option

        Returns:
            List of 4 code line strings
        """
        # Build context from history using utility function
        from bot.utils import build_code_from_history

        code_context: str = build_code_from_history(chat_history)

        prompt = PROMPT_CODE_GENERATION.format(
            max_length=max_length,
            code_context=code_context if code_context else DEFAULT_CODE_CONTEXT,
        )

        try:
            return await self._generate_with_api(prompt, max_length)
        except Exception as e:
            print(ERROR_GENERATING_OPTIONS.format(provider=self.provider, error=e))
            return self._fallback_options(code_context)

    async def _generate_with_api(self, prompt: str, max_length: int) -> List[str]:
        """Генерация через OpenAI-совместимый API (Groq или OpenAI)."""
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            temperature=0.8,
        )

        content = response.choices[0].message.content
        parsed = json.loads(content)
        options = parsed.get("options", [])

        if len(options) != 4:
            return self._fallback_options("")

        # Truncate to max_length
        options: List[str] = [str(opt)[:max_length] for opt in options]

        # Pad if needed
        while len(options) < 4:
            options.extend(self._fallback_options("")[: 4 - len(options)])

        return options[:4]

    def _fallback_options(self, code_context: str) -> List[str]:
        """Generate fallback options if LLM fails."""
        return FALLBACK_CODE_OPTIONS[:4]

    async def complete_code(self, code: str, language: str = DEFAULT_LANGUAGE) -> str:
        """
        Complete code to be compilable without adding new logic.

        Args:
            code: Current code string
            language: Programming language

        Returns:
            Completed, compilable code
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
            print(ERROR_COMPLETING_CODE.format(provider=self.provider, error=e))
            return code  # Return original if completion fails
