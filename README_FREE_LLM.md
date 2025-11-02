# Бесплатные варианты LLM для бота

Этот проект поддерживает несколько бесплатных вариантов для генерации кода через LLM.

## 🆓 Бесплатные варианты

### 1. Groq API (Рекомендуется!)

**Преимущества:**
- ✅ Бесплатный tier
- ✅ Очень быстрый (GPU ускорение)
- ✅ Хорошее качество ответов
- ✅ Простая интеграция (совместим с OpenAI API)

**Как получить:**
1. Зарегистрируйтесь на https://console.groq.com/
2. Создайте API ключ
3. Добавьте в `.env`:
   ```
   GROQ_API_KEY=your_groq_api_key_here
   ```

**Использование:**
- Добавьте `GROQ_API_KEY` в `.env`
- Запустите `example.py` для тестирования
- В коде можно использовать `FreeLLMService(provider="groq")`

---

### 2. Ollama (Локальный, полностью бесплатный)

**Преимущества:**
- ✅ Полностью бесплатный
- ✅ Работает локально (приватность)
- ✅ Не требует интернет после установки
- ✅ Множество моделей на выбор

**Недостатки:**
- ⚠️ Требует установки
- ⚠️ Нужны ресурсы компьютера

**Установка:**
1. Скачайте и установите https://ollama.ai/
2. Запустите: `ollama serve`
3. Загрузите модель: `ollama pull llama3.2`
4. Добавьте в `.env` (опционально):
   ```
   OLLAMA_BASE_URL=http://localhost:11434
   OLLAMA_MODEL=llama3.2
   ```

**Использование:**
- Убедитесь, что Ollama запущен: `ollama serve`
- Запустите `example.py` для тестирования

---

### 3. Hugging Face Inference API

**Преимущества:**
- ✅ Бесплатный tier
- ✅ Хороший выбор моделей
- ✅ Простое использование

**Как получить:**
1. Зарегистрируйтесь на https://huggingface.co/
2. Создайте токен: https://huggingface.co/settings/tokens
3. Добавьте в `.env`:
   ```
   HUGGINGFACE_API_KEY=your_huggingface_token_here
   ```

---

## 🧪 Тестирование

Запустите `example.py` чтобы протестировать все варианты:

```bash
poetry run python example.py
```

Или:

```bash
python example.py
```

Скрипт протестирует все доступные провайдеры и покажет какие работают.

## 💡 Использование в боте

### Вариант 1: Использовать Groq вместо OpenAI

В `bot/main.py` замените:

```python
from bot.llm_service import LLMService
```

на:

```python
from bot.llm_service_free import FreeLLMService
```

И измените инициализацию:

```python
llm_service = FreeLLMService(provider="groq")
```

### Вариант 2: Автоматический выбор

Можно модифицировать `bot/main.py` чтобы автоматически выбирать доступный провайдер:

```python
from bot.llm_service_free import FreeLLMService

# Автоматический выбор провайдера
if Config.GROQ_API_KEY:
    llm_service = FreeLLMService(provider="groq")
elif Config.HUGGINGFACE_API_KEY:
    llm_service = FreeLLMService(provider="huggingface")
elif Config.OPENAI_API_KEY:
    llm_service = FreeLLMService(provider="openai")
else:
    # Fallback на Ollama
    llm_service = FreeLLMService(provider="ollama")
```

## 📊 Сравнение вариантов

| Провайдер | Скорость | Качество | Бесплатный tier | Установка |
|-----------|----------|----------|-----------------|-----------|
| **Groq** | ⚡⚡⚡ Очень быстро | ⭐⭐⭐ Хорошо | ✅ Да | ❌ Не нужна |
| **Ollama** | ⚡⚡ Зависит от CPU/GPU | ⭐⭐⭐ Хорошо | ✅ Да | ✅ Нужна |
| **Hugging Face** | ⚡ Средне | ⭐⭐ Средне | ✅ Да | ❌ Не нужна |
| **OpenAI** | ⚡⚡ Быстро | ⭐⭐⭐⭐ Отлично | ⚠️ Платный | ❌ Не нужна |

## 🎯 Рекомендация

**Для начала:** Используйте **Groq API** - это самый простой и быстрый бесплатный вариант!

1. Получите ключ на https://console.groq.com/
2. Добавьте `GROQ_API_KEY` в `.env`
3. Запустите `example.py` для проверки
4. Если работает - используйте в боте!

## 🔧 Настройка

Все настройки добавляются в файл `.env`:

```env
# Groq (рекомендуется для бесплатного использования)
GROQ_API_KEY=your_groq_api_key_here

# Ollama (локальный)
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.2

# Hugging Face
HUGGINGFACE_API_KEY=your_huggingface_token_here

# OpenAI (если нужно)
OPENAI_API_KEY=your_openai_api_key_here
```

## ❓ Проблемы?

Если что-то не работает:

1. Проверьте, что ключи добавлены в `.env`
2. Запустите `example.py` для диагностики
3. Проверьте логи в `bot.log`

