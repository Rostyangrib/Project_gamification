# ml/ai_analyzer.py
# Модуль для анализа задач с помощью AI (Groq API)

import os  # Для работы с переменными окружения и путями файлов
import requests  # Для выполнения HTTP запросов к Groq API
import json  # Для парсинга JSON ответов от API
import time  # Для реализации задержек при повторных попытках запросов
from typing import Dict, Any  # Для типизации возвращаемых значений функций


class GroqRateLimitError(Exception):
    """
    Специальное исключение для ошибок rate limit Groq API.
    Пробрасывается когда исчерпаны все попытки retry при ошибке 429.
    """
    pass


class GroqAPIError(Exception):
    """
    Общее исключение для ошибок Groq API.
    Используется для других ошибок API (не rate limit).
    """
    pass

# Получаем первый API ключ из переменных окружения (для основных запросов)
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
# Проверяем наличие основного ключа, без него работа невозможна
if not GROQ_API_KEY:
    raise EnvironmentError("GROQ_API_KEY не задан. Установите переменную окружения.")

# Получаем второй API ключ для оценки сложности (опционально, для распределения нагрузки)
# Если второй ключ не задан, будет использоваться первый ключ для всех запросов
GROQ_API_KEY_SECONDARY = os.getenv("GROQ_API_KEY_SECONDARY", GROQ_API_KEY)

# URL эндпоинта Groq API для chat completions
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
# Название модели для использования (быстрая модель Llama 3.1)
MODEL_NAME = "llama-3.1-8b-instant"

# Формируем полный путь к файлу с примерами задач для обучения модели
_EXAMPLES_PATH = os.path.join(os.path.dirname(__file__), "task_examples.txt")
try:
    # Пытаемся прочитать файл с примерами задач
    with open(_EXAMPLES_PATH, "r", encoding="utf-8") as f:
        TASK_EXAMPLES = f.read()
except Exception:
    # Если файл не найден или ошибка чтения, используем пустую строку
    TASK_EXAMPLES = ""

# Формируем полный путь к файлу с примерами оценки сложности
_COMPLEXITY_EXAMPLES_PATH = os.path.join(os.path.dirname(__file__), "complexity_examples.txt")
try:
    # Пытаемся прочитать файл с примерами оценки сложности
    with open(_COMPLEXITY_EXAMPLES_PATH, "r", encoding="utf-8") as f:
        COMPLEXITY_EXAMPLES = f.read()
except Exception:
    # Если файл не найден или ошибка чтения, используем пустую строку
    COMPLEXITY_EXAMPLES = ""

def _call_groq_with_messages(messages: list, temperature: float = 0.3, max_tokens: int = 1024, json_mode: bool = False, use_secondary_key: bool = False) -> dict:
    """
    Выполняет запрос к Groq API и возвращает распарсенный JSON ответ.
    Включает механизм повторных попыток при ошибках rate limit.
    
    Args:
        messages: Список сообщений для модели в формате [{"role": "...", "content": "..."}]
        temperature: Креативность ответа (0.0 - детерминированный, 1.0 - креативный)
        max_tokens: Максимальное количество токенов в ответе
        json_mode: Если True, модель будет возвращать только валидный JSON
        use_secondary_key: Если True, использует вторичный API ключ (для распределения нагрузки)
    
    Returns:
        dict: Распарсенный JSON ответ от модели
    """
    # Выбираем какой API ключ использовать для этого запроса
    api_key = GROQ_API_KEY_SECONDARY if use_secondary_key else GROQ_API_KEY
    
    # Формируем заголовки для HTTP запроса с авторизацией
    headers = {
        "Authorization": f"Bearer {api_key}",  # Bearer токен для аутентификации (основной или вторичный)
        "Content-Type": "application/json"  # Указываем, что отправляем JSON
    }

    # Формируем тело запроса с параметрами для модели
    payload = {
        "model": MODEL_NAME,  # Используемая языковая модель
        "messages": messages,  # Массив сообщений (системный промпт + запрос пользователя)
        "temperature": temperature,  # Степень случайности в ответах модели
        "max_tokens": max_tokens,  # Лимит токенов для ответа
        "top_p": 1,  # Nucleus sampling (1 = рассматриваем все токены)
        "stream": False,  # Отключаем потоковую передачу (получаем полный ответ сразу)
    }

    # Если требуется JSON режим, добавляем соответствующий параметр
    if json_mode:
        payload["response_format"] = {"type": "json_object"}  # Форсируем JSON ответ от модели

    # Параметры для механизма повторных попыток
    max_retries = 3  # Максимальное количество попыток запроса
    retry_delay = 2  # Начальная задержка в секундах между попытками
    
    # Цикл повторных попыток
    for attempt in range(max_retries):
        try:
            # Выполняем POST запрос к Groq API
            response = requests.post(GROQ_API_URL, headers=headers, json=payload, timeout=30)
            # Проверяем статус ответа, выбрасываем исключение при ошибках HTTP
            response.raise_for_status()
            # Извлекаем текстовый контент ответа из первого варианта (choices[0])
            content = response.json()["choices"][0]["message"]["content"]
            # Парсим JSON строку и возвращаем как словарь Python
            return json.loads(content)
        except requests.exceptions.HTTPError as e:
            # Обрабатываем HTTP ошибки (например, 429 Too Many Requests)
            if e.response.status_code == 429:
                if attempt < max_retries - 1:
                    # Если превышен rate limit и есть еще попытки
                    wait_time = retry_delay * (attempt + 1)  # Увеличиваем время ожидания с каждой попыткой
                    print(f"Rate limit exceeded, waiting {wait_time}s before retry {attempt + 2}/{max_retries}")
                    time.sleep(wait_time)  # Ждем перед следующей попыткой
                else:
                    # Если попытки исчерпаны, пробрасываем специальное исключение для rate limit
                    raise GroqRateLimitError(f"Groq API rate limit exceeded after {max_retries} attempts") from e
            else:
                # Для других HTTP ошибок пробрасываем общее исключение
                if attempt < max_retries - 1:
                    wait_time = retry_delay * (attempt + 1)
                    print(f"HTTP error {e.response.status_code}, waiting {wait_time}s before retry {attempt + 2}/{max_retries}")
                    time.sleep(wait_time)
                else:
                    raise GroqAPIError(f"Groq API error {e.response.status_code} after {max_retries} attempts") from e
        except Exception as e:
            # Обрабатываем любые другие ошибки (сетевые, таймауты и т.д.)
            if attempt < max_retries - 1:
                # Если есть еще попытки, логируем ошибку и повторяем
                print(f"Error calling Groq API (attempt {attempt + 1}/{max_retries}): {e}")
                time.sleep(retry_delay)  # Ждем перед следующей попыткой
            else:
                # Если попытки исчерпаны, пробрасываем ошибку дальше
                raise


def analyze_task(title: str, description: str = "") -> Dict[str, Any]:
    """
    Оценивает сложность выполнения задачи с помощью AI.
    
    Args:
        title: Название задачи
        description: Описание задачи (опционально)
    
    Returns:
        Dict с полями:
            - estimated_points: Оценка сложности (1-100)
            - explanation: Обоснование оценки
            - model_used: Название использованной модели
            - confidence: Уверенность модели в оценке (0.0-1.0)
    """
    # Системный промпт - инструкция для модели по оценке сложности задач
    system_prompt = f"""Ты — эксперт по оценке задач для геймификации.
Оцени сложность ВЫПОЛНЕНИЯ задачи (не срочность и не важность!) по шкале от 1 до 100:

- 1–20: можно сделать за 5–15 минут, не требует специальных знаний (например: «отправить отчёт», «купить молоко»)
- 21–50: занимает 30+ минут или требует базовых профессиональных навыков (например: «написать отчёт», «настроить Wi-Fi»)
- 51–80: требует анализа, проектирования или нескольких этапов (например: «разработать API», «провести A/B-тест»)
- 81–100: сложный проект с неопределённостью, требует координации, экспертизы и/или инноваций

Верни ТОЛЬКО корректный JSON в формате:
{{
  "estimated_points": 42,
  "explanation": "Краткое обоснование",
  "confidence": 0.95
}}

Примеры:
{COMPLEXITY_EXAMPLES}"""  # Вставляем примеры из файла для few-shot learning

    # Промпт пользователя - данные задачи для оценки
    user_prompt = f"Название: {title}\nОписание: {description}"

    try:
        # Формируем массив сообщений: системная инструкция + запрос
        messages = [
            {"role": "system", "content": system_prompt},  # Роль и поведение AI
            {"role": "user", "content": user_prompt}  # Данные для анализа
        ]
        # Вызываем API с низкой temperature для более детерминированных оценок
        # Используем вторичный ключ для оценки сложности, чтобы распределить нагрузку
        data = _call_groq_with_messages(messages, temperature=0.2, max_tokens=400, json_mode=True, use_secondary_key=True)

        # Извлекаем и нормализуем оценку сложности (гарантируем диапазон 1-100)
        points = max(1, min(100, int(data.get("estimated_points", 50))))
        # Извлекаем и нормализуем уверенность модели (гарантируем диапазон 0.0-1.0)
        conf = max(0.0, min(1.0, float(data.get("confidence", 0.7))))

        # Возвращаем структурированный результат анализа
        return {
            "estimated_points": points,  # Оценка сложности
            "explanation": str(data.get("explanation", "Оценка по умолчанию")),  # Обоснование
            "model_used": MODEL_NAME,  # Какая модель использовалась
            "confidence": conf  # Уверенность модели в оценке
        }

    except (GroqRateLimitError, GroqAPIError) as e:
        # Пробрасываем ошибки API дальше, чтобы они могли быть обработаны на уровне API
        # Это позволит тестам фиксировать ошибки rate limit
        raise
    except Exception as e:
        # В случае других ошибок (парсинг, сеть и т.д.) возвращаем дефолтные значения
        print(f"analyze_task error: {e}")
        return {
            "estimated_points": 50,  # Средняя сложность по умолчанию
            "explanation": "Ошибка анализа задачи. Использовано значение по умолчанию.",
            "model_used": "fallback",  # Указываем что это fallback значение
            "confidence": 0.0  # Нулевая уверенность при ошибке
        }


def analyze_task_with_commands(
    user_message: str,
    available_statuses: list = None,  
    available_tags: list = None       
) -> dict:
    """
    Парсит естественный язык и преобразует его в структурированную команду создания задачи.
    Также автоматически оценивает сложность задачи с помощью AI.
    
    Args:
        user_message: Сообщение пользователя на естественном языке
        available_statuses: Список доступных статусов (не используется, есть фиксированный список)
        available_tags: Список доступных тегов (не используется, есть фиксированный список)
    
    Returns:
        Dict с полями:
            - reply: Текстовый ответ пользователю
            - commands: Массив команд для выполнения (обычно create_task)
    """
    
    # Фиксированный список тегов срочности для задач
    FIXED_TAGS = ["несрочно", "срочно", "очень срочно"]
    # Фиксированный список возможных статусов задач
    FIXED_STATUSES = [
        {"code": "todo", "name": "К выполнению"},
        {"code": "in_progress", "name": "В работе"},
        {"code": "done", "name": "Выполнено"}
    ]
    # Извлекаем только коды статусов для валидации
    status_codes = [s["code"] for s in FIXED_STATUSES]
    # Форматируем список статусов для промпта (код + название)
    status_str = ", ".join([f"{s['code']} ({s['name']})" for s in FIXED_STATUSES])
    # Форматируем список тегов для промпта
    tags_str = ", ".join(FIXED_TAGS)

    # Детальный системный промпт с правилами парсинга естественного языка в структурированные команды
    system_prompt = f"""Ты — строгий ассистент для создания задач. Всегда возвращай ТОЛЬКО корректный JSON без пояснений.

ДОСТУПНЫЕ СТАТУСЫ (используй ТОЛЬКО code из списка):
{status_str}

ДОСТУПНЫЕ ТЕГИ СРОЧНОСТИ (ТОЛЬКО в нижнем регистре, ТОЛЬКО из списка):
{tags_str}

ПРАВИЛА:
1. Если запрос содержит оскорбления, травлю, дискриминацию, насилие, незаконные действия или призывы к ним:
   - НЕ СОЗДАВАЙ никаких задач.
   - Возвращай JSON ТОЛЬКО в виде:
     {{
       "reply": "Я не могу помочь с задачами, связанными с оскорблениями, травлей, дискриминацией или вредом другим.",
       "commands": []
     }}

2. due_date: только если указана точная дата ДД.ММ.ГГГГ → преобразуй в "ГГГГ-ММ-ДДT00:00:00". Иначе null.
3. title — краткий, ясный, без "создай задачу".
4. В поле "tags" указывай ТОЛЬКО один тег срочности, если он явно упомянут:
   - "срочно", "важно", "надо срочно" → ["срочно"]
   - "очень срочно", "критично", "немедленно" → ["очень срочно"]
   - "несрочно", "когда успеешь", "не горит" → ["несрочно"]
   - иначе → []
5. Никогда не добавляй другие теги — только срочность!
6. status_code — ТОЛЬКО один из: {", ".join(status_codes)}
7. Если ты не уверен в срочности или дате, устанавливай:
   - "tags": []
   - "due_date": null
8. Поле "reply" делай кратким:
   - "Создаю задачу '<title>'"
   - "Создаю срочную задачу '<title>'"
   - "Создаю критическую задачу '<title>'"
   - "Не могу создать такую задачу."
9. Если формулировка непонятна, бессмысленна или description пуст — ВОЗВРАЩАЙ:
   {{
     "reply": "Формулировка задачи непонятна. Пожалуйста, переформулируйте запрос более конкретно (что именно нужно сделать, где, к какому результату и в какие сроки прийти).",
     "commands": []
   }}
10. description ДОЛЖНО быть осмысленным и непустым.

Формат ответа СТРОГО как в примерах. Никаких отклонений!

{TASK_EXAMPLES}"""  # Вставляем примеры из файла для обучения модели правильному формату ответа

    try:
        # Формируем сообщения: системная инструкция + запрос пользователя
        messages = [
            {"role": "system", "content": system_prompt},  # Инструкция как парсить задачи
            {"role": "user", "content": user_message}  # Сообщение пользователя для парсинга
        ]
        # Вызываем API с очень низкой temperature для максимально детерминированного парсинга
        raw_data = _call_groq_with_messages(messages, temperature=0.05, max_tokens=600, json_mode=True)

        # Извлекаем текстовый ответ для пользователя
        reply = raw_data.get("reply", "Готов помочь!")
        # Извлекаем массив команд (обычно одна команда create_task)
        commands = raw_data.get("commands", [])

        # ВАЖНО: Для каждой команды создания задачи добавляем оценку сложности
        for cmd in commands:
            if cmd.get("action") == "create_task":  # Проверяем что это команда создания задачи
                task_data = cmd.get("task_data", {})  # Получаем данные задачи
                title = task_data.get("title", "")  # Название задачи
                description = task_data.get("description", "")  # Описание задачи
                # Вызываем AI для оценки сложности (второй запрос к API)
                complexity = analyze_task(title, description)
                # Добавляем оценку сложности в данные задачи
                task_data["estimated_points"] = complexity["estimated_points"]

        # Возвращаем структурированный ответ с командами
        return {
            "reply": reply,  # Текстовый ответ пользователю
            "commands": commands  # Массив команд для выполнения
        }

    except (GroqRateLimitError, GroqAPIError) as e:
        # Пробрасываем ошибки API дальше, чтобы они могли быть обработаны на уровне API
        # Это позволит тестам фиксировать ошибки rate limit
        raise
    except Exception as e:
        # В случае других ошибок возвращаем безопасный ответ без команд
        print(f"analyze_task_with_commands error: {e}")
        return {
            "reply": "Извините, не удалось обработать ваш запрос.",  # Сообщение об ошибке
            "commands": []  # Пустой массив команд
        }