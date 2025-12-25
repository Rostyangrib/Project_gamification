# ml/ai_analyzer.py
# Модуль для анализа задач с помощью AI (Yandex Cloud API)

import os  # Для работы с переменными окружения и путями файлов
import requests  # Для выполнения HTTP запросов к Yandex Cloud API
import json  # Для парсинга JSON ответов от API
import time  # Для реализации задержек при повторных попытках запросов
from typing import Dict, Any  # Для типизации возвращаемых значений функций


class YandexRateLimitError(Exception):
    """
    Специальное исключение для ошибок rate limit Yandex Cloud API.
    Пробрасывается когда исчерпаны все попытки retry при ошибке 429.
    """
    pass


class YandexAPIError(Exception):
    """
    Общее исключение для ошибок Yandex Cloud API.
    Используется для других ошибок API (не rate limit).
    """
    pass

# Получаем API ключ из переменных окружения
YANDEX_API_KEY = os.getenv("YANDEX_API_KEY")

# Проверяем наличие ключа, без него работа невозможна
if not YANDEX_API_KEY:
    raise EnvironmentError("YANDEX_API_KEY не задан. Установите переменную окружения.")

# URL эндпоинта Yandex Cloud API для completions
YANDEX_API_URL = "https://llm.api.cloud.yandex.net/foundationModels/v1/completion"
# Название модели для использования (Llama 3.1 70B Instruct)
MODEL_NAME = "gpt://b1g58ef69g4uvpd24sk0/yandexgpt/rc"

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

def _call_yandex_with_messages(messages: list, temperature: float = 0.3, max_tokens: int = 5000, json_mode: bool = False) -> dict:
    """
    Выполняет запрос к Yandex Cloud API и возвращает распарсенный JSON ответ.
    Включает механизм повторных попыток при ошибках rate limit.
    
    Args:
        messages: Список сообщений для модели в формате [{"role": "...", "content": "..."}]
        temperature: Креативность ответа (0.0 - детерминированный, 1.0 - креативный)
        max_tokens: Максимальное количество токенов в ответе
        json_mode: Если True, модель будет возвращать только валидный JSON
    
    Returns:
        dict: Распарсенный JSON ответ от модели
    """
    # Формируем заголовки для HTTP запроса с авторизацией
    headers = {
        "Authorization": f"Api-Key {YANDEX_API_KEY}",  # Api-Key токен для аутентификации
        "Content-Type": "application/json"  # Указываем, что отправляем JSON
    }

    # Преобразуем messages в формат Yandex Cloud API
    # Yandex Cloud использует формат с modelUri и completionOptions
    system_message = None
    user_messages = []
    
    for msg in messages:
        if msg["role"] == "system":
            system_message = msg["content"]
        elif msg["role"] == "user":
            user_messages.append(msg["content"])
        elif msg["role"] == "assistant":
            user_messages.append(msg["content"])
    
    # Объединяем системный промпт с пользовательскими сообщениями
    if system_message:
        full_text = f"{system_message}\n\n" + "\n".join(user_messages)
    else:
        full_text = "\n".join(user_messages)

    # Если требуется JSON режим, добавляем инструкцию в системный промпт
    if json_mode and system_message:
        # Добавляем инструкцию о JSON формате в начало системного промпта
        full_text = system_message + "\n\nВАЖНО: Верни ТОЛЬКО валидный JSON без дополнительного текста.\n\n" + "\n".join(user_messages)
    elif json_mode and not system_message:
        # Если нет системного промпта, но нужен JSON режим, добавляем инструкцию в начало
        full_text = "ВАЖНО: Верни ТОЛЬКО валидный JSON без дополнительного текста.\n\n" + full_text
    
    # Формируем тело запроса в формате Yandex Cloud API
    payload = {
        "modelUri": MODEL_NAME,  # URI модели в формате gpt://folder-id/model/version
        "completionOptions": {
            "stream": False,  # Отключаем потоковую передачу
            "temperature": temperature,  # Степень случайности в ответах модели
            "maxTokens": int(max_tokens)  # Лимит токенов для ответа (гарантируем int)
        },
        "messages": [
            {
                "role": "user",
                "text": full_text
            }
        ]
    }

    # Параметры для механизма повторных попыток
    max_retries = 3  # Максимальное количество попыток запроса
    retry_delay = 2  # Начальная задержка в секундах между попытками
    
    # Цикл повторных попыток
    for attempt in range(max_retries):
        try:
            # Выполняем POST запрос к Yandex Cloud API
            response = requests.post(YANDEX_API_URL, headers=headers, json=payload, timeout=30)
            
            # Проверяем статус ответа
            if response.status_code != 200:
                # Логируем детали ошибки для отладки
                print(f"Yandex Cloud API error {response.status_code}: {response.text[:500]}")
                response.raise_for_status()
            
            # Проверяем, что ответ не пустой
            if not response.text or not response.text.strip():
                raise ValueError("Получен пустой ответ от Yandex Cloud API")
            
            # Извлекаем текстовый контент ответа из формата Yandex Cloud API
            try:
                response_data = response.json()
            except json.JSONDecodeError as e:
                # Если ответ не JSON, выводим его для отладки
                print(f"Ошибка парсинга JSON ответа. Статус: {response.status_code}")
                print(f"Тело ответа (первые 500 символов): {response.text[:500]}")
                raise ValueError(f"Некорректный JSON ответ от API: {str(e)}") from e
            
            # Проверяем структуру ответа
            if "result" not in response_data:
                print(f"Неожиданная структура ответа: {response_data}")
                raise ValueError(f"Неожиданная структура ответа от API: отсутствует поле 'result'")
            
            if "alternatives" not in response_data["result"] or len(response_data["result"]["alternatives"]) == 0:
                print(f"Неожиданная структура ответа: {response_data}")
                raise ValueError(f"Неожиданная структура ответа от API: отсутствуют альтернативы")
            
            content = response_data["result"]["alternatives"][0]["message"]["text"]
            
            # Если требуется JSON режим, парсим JSON
            if json_mode:
                try:
                    # Очищаем ответ от markdown код-блоков (```json ... ``` или ``` ... ```)
                    cleaned_content = content.strip()
                    
                    # Убираем markdown код-блоки, если они есть
                    if cleaned_content.startswith("```"):
                        # Находим первую закрывающую ```
                        end_marker = cleaned_content.find("```", 3)
                        if end_marker != -1:
                            # Извлекаем содержимое между маркерами
                            cleaned_content = cleaned_content[3:end_marker].strip()
                            # Убираем возможный префикс "json" после первой ```
                            if cleaned_content.startswith("json"):
                                cleaned_content = cleaned_content[4:].strip()
                        else:
                            # Если закрывающего маркера нет, просто убираем открывающий
                            cleaned_content = cleaned_content[3:].strip()
                            if cleaned_content.startswith("json"):
                                cleaned_content = cleaned_content[4:].strip()
                    
                    # Если ответ обрезан (не заканчивается на } или ]), пытаемся найти последний валидный JSON объект
                    if not (cleaned_content.endswith("}") or cleaned_content.endswith("]")):
                        # Пытаемся найти последнюю закрывающую скобку
                        last_brace = cleaned_content.rfind("}")
                        last_bracket = cleaned_content.rfind("]")
                        if last_brace > last_bracket and last_brace > 0:
                            # Пробуем обрезать до последней закрывающей скобки
                            potential_json = cleaned_content[:last_brace + 1]
                            try:
                                # Проверяем, валиден ли обрезанный JSON
                                test_parse = json.loads(potential_json)
                                cleaned_content = potential_json
                            except:
                                pass  # Если не получилось, используем оригинальный
                    
                    # Парсим очищенный JSON
                    return json.loads(cleaned_content)
                except json.JSONDecodeError as e:
                    print(f"Ошибка парсинга JSON из ответа модели.")
                    print(f"Исходный ответ (первые 500 символов): {content[:500]}")
                    print(f"Очищенный ответ (первые 500 символов): {cleaned_content[:500] if 'cleaned_content' in locals() else 'N/A'}")
                    print(f"Ошибка: {str(e)}")
                    raise ValueError(f"Модель вернула невалидный JSON: {str(e)}") from e
            else:
                # Возвращаем как обычный текст (но для совместимости с существующим кодом возвращаем dict)
                return {"content": content}
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
                    raise YandexRateLimitError(f"Yandex Cloud API rate limit exceeded after {max_retries} attempts") from e
            else:
                # Для других HTTP ошибок пробрасываем общее исключение
                if attempt < max_retries - 1:
                    wait_time = retry_delay * (attempt + 1)
                    print(f"HTTP error {e.response.status_code}, waiting {wait_time}s before retry {attempt + 2}/{max_retries}")
                    time.sleep(wait_time)
                else:
                    raise YandexAPIError(f"Yandex Cloud API error {e.response.status_code} after {max_retries} attempts") from e
        except Exception as e:
            # Обрабатываем любые другие ошибки (сетевые, таймауты и т.д.)
            if attempt < max_retries - 1:
                # Если есть еще попытки, логируем ошибку и повторяем
                print(f"Error calling Yandex Cloud API (attempt {attempt + 1}/{max_retries}): {e}")
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

ВАЖНО: Если задача бессмысленна, неконкретна, состоит из случайных слов или не может быть выполнена — верни estimated_points: null (не число!).

Критерии бессмысленной задачи:
- Название состоит из случайных слов без логической связи (например: "крокодил лампа облако")
- Формулировка не содержит конкретного действия (например: "сделать нормально все")
- Задача физически невозможна или абсурдна (например: "разукрасить радугу радугой")
- Описание пустое или повторяет название без дополнительной информации

Для осмысленных задач используй шкалу:
- 1–20: можно сделать за 5–15 минут, не требует специальных знаний (например: «отправить отчёт», «купить молоко»)
- 21–50: занимает 30+ минут или требует базовых профессиональных навыков (например: «написать отчёт», «настроить Wi-Fi»)
- 51–80: требует анализа, проектирования или нескольких этапов (например: «разработать API», «провести A/B-тест»)
- 81–100: сложный проект с неопределённостью, требует координации, экспертизы и/или инноваций

Верни ТОЛЬКО корректный JSON в формате:
Для осмысленной задачи:
{{
  "estimated_points": 42,
  "explanation": "Краткое обоснование",
  "confidence": 0.95
}}

Для бессмысленной задачи:
{{
  "estimated_points": null,
  "explanation": "Задача бессмысленна: [причина]",
  "confidence": 1.0
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
        # Увеличиваем max_tokens для полных ответов (модель может оборачивать JSON в markdown)
        data = _call_yandex_with_messages(messages, temperature=0.2, max_tokens=1000, json_mode=True)

        # Проверяем, является ли задача бессмысленной (estimated_points = null)
        estimated_points = data.get("estimated_points")
        if estimated_points is None:
            # Задача бессмысленна - возвращаем специальное значение
            return {
                "estimated_points": None,  # None означает бессмысленную задачу
                "explanation": str(data.get("explanation", "Задача бессмысленна")),
                "model_used": MODEL_NAME,
                "confidence": float(data.get("confidence", 1.0)),
                "is_meaningless": True  # Флаг для идентификации бессмысленных задач
            }
        
        # Извлекаем и нормализуем оценку сложности (гарантируем диапазон 1-100)
        points = max(1, min(100, int(estimated_points)))
        # Извлекаем и нормализуем уверенность модели (гарантируем диапазон 0.0-1.0)
        conf = max(0.0, min(1.0, float(data.get("confidence", 0.7))))

        # Возвращаем структурированный результат анализа
        return {
            "estimated_points": points,  # Оценка сложности
            "explanation": str(data.get("explanation", "Оценка по умолчанию")),  # Обоснование
            "model_used": MODEL_NAME,  # Какая модель использовалась
            "confidence": conf  # Уверенность модели в оценке
        }

    except (YandexRateLimitError, YandexAPIError) as e:
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
10. description ДОЛЖНО быть осмысленным, если не удается определить description из запроса, то description = Нет описания.

Формат ответа СТРОГО как в примерах. Никаких отклонений!

{TASK_EXAMPLES}"""  # Вставляем примеры из файла для обучения модели правильному формату ответа

    try:
        # Формируем сообщения: системная инструкция + запрос пользователя
        messages = [
            {"role": "system", "content": system_prompt},  # Инструкция как парсить задачи
            {"role": "user", "content": user_message}  # Сообщение пользователя для парсинга
        ]
        # Вызываем API с очень низкой temperature для максимально детерминированного парсинга
        # Увеличиваем max_tokens для больших JSON ответов (модель может оборачивать JSON в markdown)
        raw_data = _call_yandex_with_messages(messages, temperature=0.05, max_tokens=3000, json_mode=True)

        # Извлекаем текстовый ответ для пользователя
        reply = raw_data.get("reply", "Готов помочь!")
        # Извлекаем массив команд (обычно одна команда create_task)
        commands = raw_data.get("commands", [])

        # ВАЖНО: Для каждой команды создания задачи добавляем оценку сложности
        valid_commands = []
        for cmd in commands:
            if cmd.get("action") == "create_task":  # Проверяем что это команда создания задачи
                task_data = cmd.get("task_data", {})  # Получаем данные задачи
                title = task_data.get("title", "")  # Название задачи
                description = task_data.get("description", "")  # Описание задачи
                # Вызываем AI для оценки сложности (второй запрос к API)
                complexity = analyze_task(title, description)
                # Проверяем, является ли задача бессмысленной
                if complexity.get("estimated_points") is None or complexity.get("is_meaningless"):
                    # Если задача бессмысленная, пропускаем команду и возвращаем сообщение об ошибке
                    return {
                        "reply": f"Задача бессмысленна или неконкретна: {complexity.get('explanation', 'Не удалось оценить задачу')}",
                        "commands": []
                    }
                # Добавляем оценку сложности в данные задачи
                task_data["estimated_points"] = complexity["estimated_points"]
                valid_commands.append(cmd)
            else:
                valid_commands.append(cmd)
        
        # Обновляем список команд только валидными
        commands = valid_commands

        # Возвращаем структурированный ответ с командами
        return {
            "reply": reply,  # Текстовый ответ пользователю
            "commands": commands  # Массив команд для выполнения
        }

    except (YandexRateLimitError, YandexAPIError) as e:
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