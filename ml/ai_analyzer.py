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

_EXAMPLES_PATH = os.path.join(os.path.dirname(__file__), "task_examples.txt")
try:
    with open(_EXAMPLES_PATH, "r", encoding="utf-8") as f:
        TASK_EXAMPLES = f.read()
except Exception:
    TASK_EXAMPLES = ""

def _call_groq_with_messages(messages: list, temperature: float = 0.3, max_tokens: int = 1024, json_mode: bool = False) -> dict:
    """Выполняет запрос к Groq и возвращает JSON."""
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


def analyze_task_with_commands(
    user_message: str,
    available_statuses: list = None,
    available_tags: list = None
) -> dict:
    """Преобразует запрос пользователя в команду создания задачи с оценкой сложности — за один вызов модели."""

    FIXED_TAGS = ["несрочно", "срочно", "очень срочно"]
    FIXED_STATUSES = [
        {"code": "todo", "name": "К выполнению"},
        {"code": "in_progress", "name": "В работе"},
        {"code": "done", "name": "Выполнено"}
    ]
    status_codes = [s["code"] for s in FIXED_STATUSES]
    status_str = ", ".join([f"{s['code']} ({s['name']})" for s in FIXED_STATUSES])
    tags_str = ", ".join(FIXED_TAGS)

    system_prompt = f"""Ты — строгий ассистент для создания задач с автоматической оценкой сложности. Всегда возвращай ТОЛЬКО корректный JSON без пояснений.

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
7. Если не уверен в срочности или дате → tags: [], due_date: null.
8. description ДОЛЖНО быть осмысленным и непустым.
9. Если формулировка непонятна, бессмысленна или description пуст → верни:
   {{
     "reply": "Формулировка задачи непонятна. Пожалуйста, переформулируйте запрос более конкретно (что именно нужно сделать, где, к какому результату и в какие сроки прийти).",
     "commands": []
   }}
10. ВСЕГДА оценивай сложность задачи и ДОБАВЛЯЙ в task_data поля:
    - "estimated_points": число от 1 до 100,
    - "explanation": краткое обоснование,
    - "confidence": число от 0.0 до 1.0

ШКАЛА СЛОЖНОСТИ:
- 1–20: можно сделать за 5–15 минут, не требует специальных знаний (например: «отправить отчёт», «купить молоко»)
- 21–50: занимает 30+ минут или требует базовых профессиональных навыков (например: «написать отчёт», «настроить Wi-Fi»)
- 51–80: требует анализа, проектирования или нескольких этапов (например: «разработать API», «провести A/B-тест»)
- 81–100: сложный проект с неопределённостью, требует координации, экспертизы и/или инноваций

Формат ответа СТРОГО как в примерах. Никаких отклонений!

{TASK_EXAMPLES}"""

    try:
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message}
        ]
        raw_data = _call_groq_with_messages(messages, temperature=0.1, max_tokens=700, json_mode=True)

        reply = raw_data.get("reply", "Готов помочь!")
        commands = raw_data.get("commands", [])


        for cmd in commands:
            if cmd.get("action") == "create_task":
                task_data = cmd.get("task_data", {})
                try:
                    task_data["estimated_points"] = int(task_data.get("estimated_points", 50))
                    task_data["confidence"] = float(task_data.get("confidence", 0.7))
                except (TypeError, ValueError):
                    task_data["estimated_points"] = 50
                    task_data["confidence"] = 0.7

        return {
            "reply": reply,
            "commands": commands
        }

    except Exception as e:
        print(f"analyze_task_with_commands error: {e}")
        return {
            "reply": "Извините, не удалось обработать ваш запрос.",
            "commands": []
        }
