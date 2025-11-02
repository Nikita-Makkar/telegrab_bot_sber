"""Tests for LLM service."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from bot.llm_service_unified import UnifiedLLMService


@pytest.mark.asyncio
async def test_generate_code_options_empty_history():
    """Test generating code options with empty history."""
    with patch('bot.llm_service_unified.Config') as mock_config:
        mock_config.GROQ_API_KEY = "test_key"
        mock_config.OPENAI_API_KEY = ""
        mock_config.HUGGINGFACE_API_KEY = ""
        mock_config.OLLAMA_BASE_URL = "http://localhost:11434"
        mock_config.OLLAMA_MODEL = "llama3.2"
        mock_config.LLM_PROVIDER = ""
        mock_config.MAX_CODE_LINE_LENGTH = 95
        
        service = UnifiedLLMService(provider="groq")
        
        # Mock OpenAI client for Groq
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = '{"options": ["line1", "line2", "line3", "line4"]}'

        service.client = MagicMock()
        service.client.chat.completions.create = AsyncMock(return_value=mock_response)

        options = await service.generate_code_options([])
        assert len(options) == 4
        assert all(isinstance(opt, str) for opt in options)


@pytest.mark.asyncio
async def test_generate_code_options_with_history():
    """Test generating code options with history."""
    with patch('bot.llm_service_unified.Config') as mock_config:
        mock_config.GROQ_API_KEY = "test_key"
        mock_config.MAX_CODE_LINE_LENGTH = 95
        
        service = UnifiedLLMService(provider="groq")

        history = [
            {
                "poll_id": "poll1",
                "line_number": 1,
                "options": ["def func():", "def func():"],
                "winner_option": 0,
            }
        ]

        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = (
            '{"options": ["    pass", "    return", "    raise", "    pass"]}'
        )

        service.client = MagicMock()
        service.client.chat.completions.create = AsyncMock(return_value=mock_response)

        options = await service.generate_code_options(history)
        assert len(options) == 4


@pytest.mark.asyncio
async def test_complete_code():
    """Test completing code."""
    with patch('bot.llm_service_unified.Config') as mock_config:
        mock_config.GROQ_API_KEY = "test_key"
        
        service = UnifiedLLMService(provider="groq")

        incomplete_code = "def func():\n    pass\n    # Missing closing"

        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "def func():\n    pass\n    return None"

        service.client = MagicMock()
        service.client.chat.completions.create = AsyncMock(return_value=mock_response)

        completed = await service.complete_code(incomplete_code)
        assert completed is not None
        assert isinstance(completed, str)


@pytest.mark.asyncio
async def test_fallback_options():
    """Test fallback when LLM fails."""
    with patch('bot.llm_service_unified.Config') as mock_config:
        mock_config.GROQ_API_KEY = "test_key"
        mock_config.MAX_CODE_LINE_LENGTH = 95
        
        service = UnifiedLLMService(provider="groq")

        service.client = MagicMock()
        service.client.chat.completions.create = AsyncMock(side_effect=Exception("API Error"))

        options = await service.generate_code_options([])
        # Should return fallback options
        assert len(options) == 4
        assert all(isinstance(opt, str) for opt in options)
