# test_ollama.py
import requests

response = requests.post(
    "http://localhost:11434/api/generate",
    json={
        "model": "qwen2:0.5b",
        "prompt": "Привет!",
        "stream": False
    }
)
print(response.json()["response"])