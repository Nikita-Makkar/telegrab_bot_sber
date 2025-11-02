"""
Унифицированный LLM сервис с автоматическим выбором провайдера.

Использует Groq по умолчанию, но может переключиться на OpenAI или другие провайдеры.
"""

import json
from typing import List, Optional

from bot.config import Config


class UnifiedLLMService:
    """Унифицированный LLM сервис с поддержкой разных провайдеров."""

    def __init__(self, provider: Optional[str] = None):
        """
        Инициализация LLM сервиса с автоматическим выбором провайдера.

        Args:
            provider: "groq", "openai", "huggingface", "ollama" или None для автовыбора
        """
        # Определяем провайдера
        if provider:
            self.provider = provider.lower()
        elif Config.LLM_PROVIDER:
            self.provider = Config.LLM_PROVIDER.lower()
        else:
            # Автоматический выбор: приоритет Groq -> OpenAI -> Hugging Face
            if Config.GROQ_API_KEY:
                self.provider = "groq"
                print("🤖 Using Groq API (automatic selection)")
            elif Config.OPENAI_API_KEY:
                self.provider = "openai"
                print("🤖 Using OpenAI API (automatic selection)")
            elif Config.HUGGINGFACE_API_KEY:
                self.provider = "huggingface"
                print("🤖 Using Hugging Face API (automatic selection)")
            else:
                self.provider = "ollama"
                print("🤖 Using Ollama (automatic selection)")

        self._init_client()

    def _init_client(self):
        """Инициализация клиента для выбранного провайдера."""
        if self.provider == "groq":
            from openai import AsyncOpenAI

            if not Config.GROQ_API_KEY:
                raise ValueError("GROQ_API_KEY not found in config")

            self.client = AsyncOpenAI(
                api_key=Config.GROQ_API_KEY, base_url="https://api.groq.com/openai/v1"
            )
            self.model = "llama-3.1-8b-instant"
            print(f"✅ Initialized Groq API with model: {self.model}")

        elif self.provider == "openai":
            from openai import AsyncOpenAI

            if not Config.OPENAI_API_KEY:
                raise ValueError("OPENAI_API_KEY not found in config")

            self.client = AsyncOpenAI(api_key=Config.OPENAI_API_KEY)
            self.model = Config.OPENAI_MODEL
            print(f"✅ Initialized OpenAI API with model: {self.model}")

        elif self.provider == "huggingface":
            self.client = None  # Используем httpx напрямую
            self.model = "microsoft/Phi-3-mini-4k-instruct"
            print(f"✅ Initialized Hugging Face API with model: {self.model}")

        elif self.provider == "ollama":
            self.client = None  # Используем httpx напрямую
            self.model = Config.OLLAMA_MODEL
            self.base_url = Config.OLLAMA_BASE_URL
            print(f"✅ Initialized Ollama with model: {self.model}")

        else:
            raise ValueError(f"Unknown provider: {self.provider}")

    async def generate_code_options(
        self, chat_history: List[dict], max_length: int = 95
    ) -> List[str]:
        """
        Generate 4 syntactically correct code line options based on chat history.

        Args:
            chat_history: List of previous poll results with winner_option
            max_length: Maximum length for each option

        Returns:
            List of 4 code line strings
        """
        # Build context from history
        code_context = ""
        if chat_history:
            code_lines = []
            for item in chat_history:
                if item.get("winner_option") is not None:
                    winner_text = item["options"][item["winner_option"]]
                    code_lines.append(winner_text)
            code_context = "\n".join(code_lines)

        system_prompt = """You are a code generation assistant. Generate exactly 4 syntactically correct 
code lines that would logically follow the given code context. Each line must be:
- Syntactically correct
- No more than 95 characters
- Meaningful continuation of the code
- Different from each other (variety)

Return a JSON object with an "options" key containing an array of exactly 4 strings."""

        user_prompt = f"""Given this code context:
```
{code_context if code_context else "# Start of code"}
```

Generate 4 different next lines of code. Return JSON in this format:
{{"options": ["line1", "line2", "line3", "line4"]}}"""

        try:
            if self.provider in ["groq", "openai"]:
                return await self._generate_with_openai_api(system_prompt, user_prompt, max_length)

            elif self.provider == "huggingface":
                return await self._generate_with_huggingface(code_context, max_length)

            elif self.provider == "ollama":
                return await self._generate_with_ollama(code_context, max_length)

            else:
                raise ValueError(f"Unknown provider: {self.provider}")

        except Exception as e:
            print(f"Error generating code options with {self.provider}: {e}")
            return self._fallback_options(code_context)

    async def _generate_with_openai_api(
        self, system_prompt: str, user_prompt: str, max_length: int
    ) -> List[str]:
        """Генерация через OpenAI-совместимый API (Groq или OpenAI)."""
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            response_format={"type": "json_object"},
            temperature=0.8,
        )

        content = response.choices[0].message.content
        parsed = json.loads(content)
        options = parsed.get("options", [])

        if len(options) != 4:
            return self._fallback_options("")

        # Truncate to max_length
        options = [str(opt)[:max_length] for opt in options]

        # Pad if needed
        while len(options) < 4:
            options.extend(self._fallback_options("")[: 4 - len(options)])

        return options[:4]

    async def _generate_with_huggingface(self, code_context: str, max_length: int) -> List[str]:
        """Генерация через Hugging Face API."""
        import httpx

        if not Config.HUGGINGFACE_API_KEY:
            raise ValueError("HUGGINGFACE_API_KEY not found")

        prompt = f"""<|system|>
You are a code generation assistant. Generate exactly 4 syntactically correct code lines.
Return JSON: {{"options": ["line1", "line2", "line3", "line4"]}}<|end|>
<|user|>
Given this code context:
```
{code_context if code_context else "# Start of code"}
```
Generate 4 different next lines of code.<|end|>
<|assistant|>"""

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"https://api-inference.huggingface.co/models/{self.model}",
                headers={"Authorization": f"Bearer {Config.HUGGINGFACE_API_KEY}"},
                json={"inputs": prompt, "parameters": {"max_new_tokens": 200, "temperature": 0.8}},
            )

            if response.status_code != 200:
                raise Exception(f"HF API error: {response.status_code}")

            result = response.json()
            generated_text = (
                result[0].get("generated_text", "") if isinstance(result, list) else str(result)
            )

            # Extract JSON
            start = generated_text.find("{")
            end = generated_text.rfind("}") + 1
            if start >= 0 and end > start:
                json_text = generated_text[start:end]
                parsed = json.loads(json_text)
                options = parsed.get("options", [])
            else:
                options = self._fallback_options(code_context)

        if len(options) != 4:
            options = self._fallback_options(code_context)

        options = [str(opt)[:max_length] for opt in options]
        while len(options) < 4:
            options.extend(self._fallback_options(code_context)[: 4 - len(options)])

        return options[:4]

    async def _generate_with_ollama(self, code_context: str, max_length: int) -> List[str]:
        """Генерация через Ollama API."""
        import httpx

        prompt = f"""You are a code generation assistant. Generate exactly 4 syntactically correct code lines.
Given code context:
```
{code_context if code_context else "# Start of code"}
```

Generate 4 different next lines of code. Return JSON: {{"options": ["line1", "line2", "line3", "line4"]}}"""

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "format": "json",
                    "stream": False,
                },
            )

            if response.status_code != 200:
                raise Exception(f"Ollama error: {response.status_code}")

            result = response.json()
            generated_text = result.get("response", "")

            try:
                parsed = json.loads(generated_text)
                options = parsed.get("options", [])
            except (json.JSONDecodeError, ValueError):
                options = self._fallback_options(code_context)

        if len(options) != 4:
            options = self._fallback_options(code_context)

        options = [str(opt)[:max_length] for opt in options]
        while len(options) < 4:
            options.extend(self._fallback_options(code_context)[: 4 - len(options)])

        return options[:4]

    def _fallback_options(self, code_context: str) -> List[str]:
        """Generate fallback options if LLM fails."""
        base_lines = [
            "    # TODO: implement functionality",
            "    pass",
            "    return None",
            "    raise NotImplementedError()",
        ]
        return base_lines[:4]

    async def complete_code(self, code: str, language: str = "python") -> str:
        """
        Complete code to be compilable without adding new logic.

        Args:
            code: Current code string
            language: Programming language

        Returns:
            Completed, compilable code
        """
        system_prompt = """You are a code completion assistant. Complete the given code to make it 
syntactically correct and compilable/executable WITHOUT adding new functionality or logic. 
Only add:
- Missing closing braces/brackets
- Missing imports if referenced
- Type hints if needed for compilation
- Required function/class declarations if referenced

Do NOT add:
- New functions
- New business logic
- New features
- Comments explaining logic

Return ONLY the completed code, nothing else."""

        user_prompt = f"""Complete this {language} code to be compilable:

```
{code}
```

Return only the completed code:"""

        try:
            if self.provider in ["groq", "openai"]:
                response = await self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    temperature=0.2,
                )

                return response.choices[0].message.content.strip()
            else:
                # For other providers, use simpler completion or return original
                return code  # Fallback для других провайдеров

        except Exception as e:
            print(f"Error completing code with {self.provider}: {e}")
            return code  # Return original if completion fails
