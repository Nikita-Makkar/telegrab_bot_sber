"""Константы для бота: промпты, сообщения и значения по умолчанию."""

# Сообщения для инициализации провайдеров
MSG_GROQ_AUTO_SELECTION: str = "🤖 Using Groq API (automatic selection)"
MSG_OPENAI_AUTO_SELECTION: str = "🤖 Using OpenAI API (automatic selection)"
MSG_GROQ_INITIALIZED: str = "✅ Initialized Groq API with model: {model}"
MSG_OPENAI_INITIALIZED: str = "✅ Initialized OpenAI API with model: {model}"

# Сообщения об ошибках
ERROR_NO_LLM_KEY: str = "No LLM API key found (GROQ_API_KEY or OPENAI_API_KEY required)"
ERROR_GROQ_KEY_NOT_FOUND: str = "GROQ_API_KEY not found in config"
ERROR_OPENAI_KEY_NOT_FOUND: str = "OPENAI_API_KEY not found in config"
ERROR_UNKNOWN_PROVIDER: str = "Unknown provider: {provider}"
ERROR_GENERATING_OPTIONS: str = "Error generating code options with {provider}: {error}"
ERROR_COMPLETING_CODE: str = "Error completing code with {provider}: {error}"

# Промпты для LLM
PROMPT_CODE_GENERATION: str = """You are a code generation assistant. Generate exactly 4 syntactically correct code lines that would logically follow the given code context. Each line must be:
- Syntactically correct
- No more than {max_length} characters
- Meaningful continuation of the code
- Different from each other (variety)

Given this code context:
```
{code_context}
```

Generate 4 different next lines of code. Return JSON in this format:
{{"options": ["line1", "line2", "line3", "line4"]}}"""

PROMPT_CODE_COMPLETION: str = """You are a code completion assistant. Complete the given code to make it syntactically correct and compilable/executable WITHOUT adding new functionality or logic. 
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

Complete this {language} code to be compilable:

```
{code}
```

Return ONLY the completed code, nothing else."""

# Fallback опции при ошибке генерации
FALLBACK_CODE_OPTIONS: list = [
    "    # TODO: implement functionality",
    "    pass",
    "    return None",
    "    raise NotImplementedError()",
]

# Значения по умолчанию
DEFAULT_CODE_CONTEXT: str = "# Start of code"
DEFAULT_LANGUAGE: str = "python"


# Командные сообщения — /start
MSG_START_NOT_ADMIN: str = "❌ This command is only available to administrators."
MSG_START_INIT_ERROR: str = "❌ Bot not properly initialized."
MSG_START_SUCCESS: str = (
    "✅ Chat history cleared. First poll created!\n"
    "The bot will automatically create new polls after each closes."
)
MSG_START_NO_POLL: str = (
    "✅ Chat history cleared.\n" "⚠️ Failed to create poll. Try /sendnow to send manually."
)
MSG_START_ERROR: str = "❌ Error: {error}"

# Командные сообщения — /code
MSG_CODE_INIT_ERROR: str = "❌ Bot not properly initialized."
MSG_CODE_EMPTY: str = "📝 No code generated yet.\nUse /start to begin generating code."
MSG_CODE_ERROR: str = "❌ Error retrieving code: {error}"

# Командные сообщения — /code_completed
MSG_CODE_COMPLETED_NOT_ADMIN: str = "❌ This command is only available to administrators."
MSG_CODE_COMPLETED_INIT_ERROR: str = "❌ Bot not properly initialized."
MSG_CODE_COMPLETED_EMPTY: str = "📝 No code to complete yet."
MSG_CODE_COMPLETED_PROGRESS: str = "⏳ Completing code... This may take a moment."
MSG_CODE_COMPLETED_TRUNCATED: str = (
    "Completed code (truncated, full file will be sent as attachment):\n"
    '<pre><code class="language-python">{code}...</code></pre>'
)
MSG_CODE_COMPLETED_FULL: str = (
    "Completed code:\n" '<pre><code class="language-python">{code}</code></pre>'
)
MSG_CODE_COMPLETED_FILE_ERROR: str = "✅ Code completed, but error sending file: {error}"
MSG_CODE_COMPLETED_ERROR: str = "❌ Error completing code:\n{error}"

# Командные сообщения — /sendnow
MSG_SENDNOW_NOT_ADMIN: str = "❌ This command is only available to administrators."
MSG_SENDNOW_INIT_ERROR: str = "❌ Bot not properly initialized."
MSG_SENDNOW_ACTIVE_POLL: str = (
    "⚠️ There is already an active poll (Line {line_number}).\n"
    "Close it first or wait for it to expire."
)
MSG_SENDNOW_SUCCESS: str = "✅ New poll created and sent!"
MSG_SENDNOW_ERROR: str = "❌ Failed to create poll. Check logs for details."

# Командные сообщения — /health
MSG_HEALTH_NOT_ADMIN: str = "❌ This command is only available to administrators."
MSG_HEALTH_INIT_ERROR: str = "❌ Bot not properly initialized."
MSG_HEALTH_STATUS: str = (
    "🤖 Bot Health Status\n\n"
    "⏱️ Uptime: {uptime}\n"
    "📊 Active polls: {active_polls_count}\n"
    "{current_poll_status}"
)
MSG_HEALTH_POLL_ACTIVE: str = "📝 Current poll: Line {line_number}, closes in {minutes}m {seconds}s"
MSG_HEALTH_POLL_ACTIVE_NO_TIMER: str = "📝 Current poll: Line {line_number}"
MSG_HEALTH_NO_POLL: str = "📝 No active poll in this chat"

# Командные сообщения — /logs и /alllogs
MSG_LOGS_NOT_ADMIN: str = "❌ This command is only available to administrators."
MSG_LOGS_FILE_NOT_FOUND: str = "📄 No log file found."
MSG_LOGS_ERROR: str = "❌ Error: {error}"
MSG_ALLLOGS_FILE_NOT_FOUND: str = "📄 No log file found."

# Прочие
MSG_POLL_MANAGER_MISSING: str = "PollManager not available"

# Константа сообщения об ошибке форматирования
ERROR_FORMAT_FAILED: str = "Error occurred (could not format error message)"


# Константы для провайдеров
DEFAULT_GROQ_MODEL: str = "llama-3.1-8b-instant"
DEFAULT_OPENAI_MODEL: str = "gpt-4o-mini"
GROQ_API_BASE_URL: str = "https://api.groq.com/openai/v1"

MSG_GROQ_AUTO_SELECTION: str = "⚙️ Автоматически выбран Groq (LLM провайдер)"
MSG_OPENAI_AUTO_SELECTION: str = "⚙️ Автоматически выбран OpenAI (LLM провайдер)"
MSG_GROQ_INITIALIZED: str = "Groq инициализирован с моделью: {model}"
MSG_OPENAI_INITIALIZED: str = "OpenAI инициализирован с моделью: {model}"


ERROR_MISSING_BOT_TOKEN: str = "BOT_TOKEN is required"
ERROR_GROQ_KEY_REQUIRED: str = "GROQ_API_KEY is required when LLM_PROVIDER=groq"
ERROR_OPENAI_KEY_REQUIRED: str = "OPENAI_API_KEY is required when LLM_PROVIDER=openai"
ERROR_NO_LLM_KEYS: str = "At least one LLM API key is required: OPENAI_API_KEY or GROQ_API_KEY"
ERROR_MISSING_ADMIN_IDS: str = "ADMIN_USER_IDS is required"
