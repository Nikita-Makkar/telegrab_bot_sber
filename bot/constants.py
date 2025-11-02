"""Константы для бота: промпты, сообщения и значения по умолчанию."""

# Сообщения для инициализации провайдеров
MSG_GROQ_AUTO_SELECTION = "🤖 Using Groq API (automatic selection)"
MSG_OPENAI_AUTO_SELECTION = "🤖 Using OpenAI API (automatic selection)"
MSG_GROQ_INITIALIZED = "✅ Initialized Groq API with model: {model}"
MSG_OPENAI_INITIALIZED = "✅ Initialized OpenAI API with model: {model}"

# Сообщения об ошибках
ERROR_NO_LLM_KEY = "No LLM API key found (GROQ_API_KEY or OPENAI_API_KEY required)"
ERROR_GROQ_KEY_NOT_FOUND = "GROQ_API_KEY not found in config"
ERROR_OPENAI_KEY_NOT_FOUND = "OPENAI_API_KEY not found in config"
ERROR_UNKNOWN_PROVIDER = "Unknown provider: {provider}"
ERROR_GENERATING_OPTIONS = "Error generating code options with {provider}: {error}"
ERROR_COMPLETING_CODE = "Error completing code with {provider}: {error}"

# Промпты для LLM
PROMPT_CODE_GENERATION = """You are a code generation assistant. Generate exactly 4 syntactically correct code lines that would logically follow the given code context. Each line must be:
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

PROMPT_CODE_COMPLETION = """You are a code completion assistant. Complete the given code to make it syntactically correct and compilable/executable WITHOUT adding new functionality or logic. 
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
FALLBACK_CODE_OPTIONS = [
    "    # TODO: implement functionality",
    "    pass",
    "    return None",
    "    raise NotImplementedError()",
]

# Значения по умолчанию
DEFAULT_CODE_CONTEXT = "# Start of code"
DEFAULT_LANGUAGE = "python"


# Командные сообщения — /start
MSG_START_NOT_ADMIN = "❌ This command is only available to administrators."
MSG_START_INIT_ERROR = "❌ Bot not properly initialized."
MSG_START_SUCCESS = (
    "✅ Chat history cleared. First poll created!\n"
    "The bot will automatically create new polls after each closes."
)
MSG_START_NO_POLL = (
    "✅ Chat history cleared.\n" "⚠️ Failed to create poll. Try /sendnow to send manually."
)
MSG_START_ERROR = "❌ Error: {error}"

# Командные сообщения — /code
MSG_CODE_INIT_ERROR = "❌ Bot not properly initialized."
MSG_CODE_EMPTY = "📝 No code generated yet.\nUse /start to begin generating code."
MSG_CODE_ERROR = "❌ Error retrieving code: {error}"

# Командные сообщения — /code_completed
MSG_CODE_COMPLETED_NOT_ADMIN = "❌ This command is only available to administrators."
MSG_CODE_COMPLETED_INIT_ERROR = "❌ Bot not properly initialized."
MSG_CODE_COMPLETED_EMPTY = "📝 No code to complete yet."
MSG_CODE_COMPLETED_PROGRESS = "⏳ Completing code... This may take a moment."
MSG_CODE_COMPLETED_TRUNCATED = (
    "Completed code (truncated, full file will be sent as attachment):\n"
    '<pre><code class="language-python">{code}...</code></pre>'
)
MSG_CODE_COMPLETED_FULL = (
    "Completed code:\n" '<pre><code class="language-python">{code}</code></pre>'
)
MSG_CODE_COMPLETED_FILE_ERROR = "✅ Code completed, but error sending file: {error}"
MSG_CODE_COMPLETED_ERROR = "❌ Error completing code:\n{error}"

# Командные сообщения — /sendnow
MSG_SENDNOW_NOT_ADMIN = "❌ This command is only available to administrators."
MSG_SENDNOW_INIT_ERROR = "❌ Bot not properly initialized."
MSG_SENDNOW_ACTIVE_POLL = (
    "⚠️ There is already an active poll (Line {line_number}).\n"
    "Close it first or wait for it to expire."
)
MSG_SENDNOW_SUCCESS = "✅ New poll created and sent!"
MSG_SENDNOW_ERROR = "❌ Failed to create poll. Check logs for details."

# Командные сообщения — /health
MSG_HEALTH_NOT_ADMIN = "❌ This command is only available to administrators."
MSG_HEALTH_INIT_ERROR = "❌ Bot not properly initialized."
MSG_HEALTH_STATUS = (
    "🤖 Bot Health Status\n\n"
    "⏱️ Uptime: {uptime}\n"
    "📊 Active polls: {active_polls_count}\n"
    "{current_poll_status}"
)
MSG_HEALTH_POLL_ACTIVE = "📝 Current poll: Line {line_number}, closes in {minutes}m {seconds}s"
MSG_HEALTH_POLL_ACTIVE_NO_TIMER = "📝 Current poll: Line {line_number}"
MSG_HEALTH_NO_POLL = "📝 No active poll in this chat"

# Командные сообщения — /logs и /alllogs
MSG_LOGS_NOT_ADMIN = "❌ This command is only available to administrators."
MSG_LOGS_FILE_NOT_FOUND = "📄 No log file found."
MSG_LOGS_ERROR = "❌ Error: {error}"
MSG_ALLLOGS_FILE_NOT_FOUND = "📄 No log file found."

# Прочие
MSG_POLL_MANAGER_MISSING = "PollManager not available"

# Константа сообщения об ошибке форматирования
ERROR_FORMAT_FAILED = "Error occurred (could not format error message)"
