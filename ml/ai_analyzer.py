# ml/ai_analyzer.py
import os
import requests
import json
from typing import Dict, Any

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
if not GROQ_API_KEY:
    raise EnvironmentError("GROQ_API_KEY не задан. Установите переменную окружения.")

GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
MODEL_NAME = "llama-3.1-8b-instant"


def _call_groq_with_messages(messages: list, temperature: float = 0.3, max_tokens: int = 1024, json_mode: bool = False) -> dict:
    """выполняет запрос к грок и возвращает нормальный json."""
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": MODEL_NAME,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "top_p": 1,
        "stream": False,
    }

    if json_mode:
        payload["response_format"] = {"type": "json_object"}

    response = requests.post(GROQ_API_URL, headers=headers, json=payload, timeout=30)
    response.raise_for_status()
    content = response.json()["choices"][0]["message"]["content"]
    return json.loads(content)


def analyze_task(title: str, description: str = "") -> Dict[str, Any]:
    """оценивает сложность задачи от 1до 100 и возвращает ответ"""
    system_prompt = """Ты — эксперт по оценке задач для геймификации.
Оцени задачу по шкале от 1 до 100 баллов:
- 1–20: очень простая (бытовые дела, рутина)
- 21–50: средняя (рабочие задачи, требует времени)
- 51–80: сложная (проекты, аналитика, креатив)
- 81–100: очень важная/сложная (стратегические, срочные, сложные проекты)

Верни ТОЛЬКО JSON в формате:
{
  "estimated_points": 42,
  "explanation": "Краткое обоснование",
  "confidence": 0.95
}"""

    user_prompt = f"Название: {title}\nОписание: {description}"

    try:
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        data = _call_groq_with_messages(messages, temperature=0.2, max_tokens=500, json_mode=True)

        points = max(1, min(100, int(data.get("estimated_points", 50))))
        conf = max(0.0, min(1.0, float(data.get("confidence", 0.7))))

        return {
            "estimated_points": points,
            "explanation": str(data.get("explanation", "Оценка по умолчанию")),
            "model_used": MODEL_NAME,
            "confidence": conf
        }

    except Exception as e:
        print(f"️ analyze_task error: {e}")
        return {
            "estimated_points": 50,
            "explanation": "Ошибка анализа задачи. Использовано значение по умолчанию.",
            "model_used": "fallback",
            "confidence": 0.0
        }


def analyze_task_with_commands(
    user_message: str,
    available_statuses: list,
    available_tags: list
) -> dict:
    """преобразует запрос пользователя в промпт для модели"""
    FIXED_TAGS = ["несрочно", "срочно", "очень срочно"]
    FIXED_STATUSES = [
        {"code": "todo", "name": "К выполнению"},
        {"code": "in_progress", "name": "В работе"},
        {"code": "done", "name": "Выполнено"}
    ]

    status_codes = [s["code"] for s in FIXED_STATUSES]
    status_str = ", ".join([f"{s['code']} ({s['name']})" for s in FIXED_STATUSES])
    tags_str = ", ".join(FIXED_TAGS)

    system_prompt = f"""Ты — строгий ассистент для создания задач. Всегда возвращай ТОЛЬКО корректный JSON без пояснений.

ДОСТУПНЫЕ СТАТУСЫ (используй ТОЛЬКО code из списка):
{status_str}

ДОСТУПНЫЕ ТЕГИ СРОЧНОСТИ (ТОЛЬКО в нижнем регистре, ТОЛЬКО из списка):
{tags_str}

ПРАВИЛА:
1. due_date: только если указана точная дата ДД.ММ.ГГГГ → преобразуй в "ГГГГ-ММ-ДДT00:00:00". Иначе null.
2. title — краткий, ясный, без "создай задачу".
3. В поле "tags" указывай **ТОЛЬКО один тег срочности**, если он явно упомянут:
   - "срочно", "важно", "надо срочно" → ["срочно"]
   - "очень срочно", "критично", "немедленно" → ["очень срочно"]
   - "несрочно", "когда успеешь", "не горит" → ["несрочно"]
   - иначе → []
4. Никогда не добавляй другие теги — только срочность!
5. status_code — ТОЛЬКО один из: {", ".join(status_codes)}
6. Формат ответа СТРОГО:
{{
  "reply": "Краткий ответ",
  "commands": [{{
    "action": "create_task",
    "task_data": {{
      "title": "...",
      "description": "...",
      "status_code": "todo",
      "due_date": null,
      "tags": ["срочно"]
    }}
  }}]
}}

ПРИМЕРЫ:

Запрос: "купить молоко завтра"
Ответ: {{
  "reply": "Создаю задачу 'Купить молоко'",
  "commands": [{{
    "action": "create_task",
    "task_data": {{
      "title": "Купить молоко",
      "description": "",
      "status_code": "todo",
      "due_date": null,
      "tags": []
    }}
  }}]
}}

Запрос: "важная встреча с клиентом 15.12.2024, подготовить документы"
Ответ: {{
  "reply": "Создаю задачу 'Встреча с клиентом'",
  "commands": [{{
    "action": "create_task",
    "task_data": {{
      "title": "Встреча с клиентом",
      "description": "Подготовить документы",
      "status_code": "todo",
      "due_date": "2024-12-15T00:00:00",
      "tags": ["срочно"]
    }}
  }}]
}}

Запрос: "нужно починить кран дома, срочно"
Ответ: {{
  "reply": "Создаю срочную задачу 'Починить кран'",
  "commands": [{{
    "action": "create_task",
    "task_data": {{
      "title": "Починить кран",
      "description": "",
      "status_code": "todo",
      "due_date": null,
      "tags": ["срочно"]
    }}
  }}]
}}

Запрос: "записать идеи для проекта"
Ответ: {{
  "reply": "Создаю задачу 'Записать идеи для проекта'",
  "commands": [{{
    "action": "create_task",
    "task_data": {{
      "title": "Записать идеи для проекта",
      "description": "",
      "status_code": "todo",
      "due_date": null,
      "tags": []
    }}
  }}]
}}

Запрос: "срочно доделать отчет к утру"
Ответ: {{
  "reply": "Создаю срочную задачу 'Доделать отчет'",
  "commands": [{{
    "action": "create_task",
    "task_data": {{
      "title": "Доделать отчет",
      "description": "",
      "status_code": "todo",
      "due_date": null,
      "tags": ["очень срочно"]
    }}
  }}]
}}

Запрос: "прочитать книгу 'Алхимик', когда будет время"
Ответ: {{
  "reply": "Создаю задачу 'Прочитать книгу \"Алхимик\"'",
  "commands": [{{
    "action": "create_task",
    "task_data": {{
      "title": "Прочитать книгу \"Алхимик\"",
      "description": "",
      "status_code": "todo",
      "due_date": null,
      "tags": ["несрочно"]
    }}
  }}]
}}

Запрос: "подготовить презентацию к выступлению 25.06.2025"
Ответ: {{
  "reply": "Создаю задачу 'Подготовить презентацию'",
  "commands": [{{
    "action": "create_task",
    "task_data": {{
      "title": "Подготовить презентацию",
      "description": "К выступлению",
      "status_code": "todo",
      "due_date": "2025-06-25T00:00:00",
      "tags": ["срочно"]
    }}
  }}]
}}

Запрос: "решить проблему с сервером, он упал!"
Ответ: {{
  "reply": "Создаю критическую задачу 'Решить проблему с сервером'",
  "commands": [{{
    "action": "create_task",
    "task_data": {{
      "title": "Решить проблему с сервером",
      "description": "Сервер упал",
      "status_code": "todo",
      "due_date": null,
      "tags": ["очень срочно"]
    }}
  }}]
}}

Запрос: "обдумать стратегию развития на следующий квартал"
Ответ: {{
  "reply": "Создаю задачу 'Обдумать стратегию развития'",
  "commands": [{{
    "action": "create_task",
    "task_data": {{
      "title": "Обдумать стратегию развития",
      "description": "На следующий квартал",
      "status_code": "todo",
      "due_date": null,
      "tags": []
    }}
  }}]
}}

Запрос: "оплатить коммунальные счета до 10.07.2025"
Ответ: {{
  "reply": "Создаю задачу 'Оплатить коммунальные счета'",
  "commands": [{{
    "action": "create_task",
    "task_data": {{
      "title": "Оплатить коммунальные счета",
      "description": "",
      "status_code": "todo",
      "due_date": "2025-07-10T00:00:00",
      "tags": ["срочно"]
    }}
  }}]
}}

Формат ответа СТРОГО как в примерах. Никаких отклонений!"""

    try:
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message}
        ]
        data = _call_groq_with_messages(messages, temperature=0.1, max_tokens=1000, json_mode=True)

        return {
            "reply": data.get("reply", "Готов помочь!"),
            "commands": data.get("commands", [])
        }

    except Exception as e:
        print(f"️ analyze_task_with_commands error: {e}")
        return {
            "reply": "Извините, не удалось обработать ваш запрос.",
            "commands": []
        }