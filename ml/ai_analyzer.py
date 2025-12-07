# ml/ai_analyzer.py
import requests
import json
from typing import Dict, Any

OLLAMA_API_BASE = "http://localhost:11434/api/generate"

def analyze_task(title: str, description: str = "") -> Dict[str, Any]:
    """
    Анализирует задачу с помощью Ollama и возвращает:
    - estimated_points: int (баллы)
    - explanation: str (объяснение модели)
    - model_used: str
    - confidence: float (0.0–1.0)
    """
    prompt = f"""Ты — эксперт по оценке сложности и ценности задач для геймификации.
    Оцени задачу по шкале от 1 до 100 баллов, где:
    - 1–20: очень простая/рутинная задача
    - 21–50: средняя задача, требует усилий
    - 51–80: сложная задача, требует времени/навыков
    - 81–100: очень сложная/важная задача

    Задача:
    Название: {title}
    Описание: {description}

    Верни ОДИН JSON объект с полями:
    {{
      "estimated_points": <число от 1 до 100>,
      "explanation": "<краткое объяснение почему такая оценка>",
      "model_used": "phi3",
      "confidence": <число от 0.0 до 1.0>
    }}
    """

    try:
        response = requests.post(
            OLLAMA_API_BASE,
            json={
                "model": "phi3",
                "prompt": prompt,
                "stream": False,
                "format": "json"
            },
            timeout=30
        )

        if response.status_code != 200:
            raise Exception(f"Ollama API error: {response.text}")

        result = response.json()

        if isinstance(result.get("response"), str):
            data = json.loads(result["response"])
        else:
            data = result.get("response", {})

        if not isinstance(data, dict):
            raise Exception("Invalid response format from model")

        required_keys = ["estimated_points", "explanation", "model_used", "confidence"]
        for key in required_keys:
            if key not in data:
                raise Exception(f"Missing key in AI response: {key}")

        data["estimated_points"] = max(1, min(100, int(data["estimated_points"])))
        data["confidence"] = max(0.0, min(1.0, float(data["confidence"])))

        return data

    except Exception as e:
        print(f"AI Analysis Error: {e}")
        return {
            "estimated_points": 50,
            "explanation": "Ошибка анализа задачи. Использовано значение по умолчанию.",
            "model_used": "fallback",
            "confidence": 0.0
        }
