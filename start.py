#!/usr/bin/env python3
"""
Скрипт запуска приложения с опциональной инициализацией БД.
Гарантирует, что инициализация БД происходит только один раз до запуска приложения.
"""
import os
from dotenv import load_dotenv

load_dotenv()

if __name__ == "__main__":
    if os.getenv("INIT_DB", "false").lower() == "true":
        print("Инициализация базы данных...")
        from database import init_db
        init_db()
        print("Инициализация завершена.")
    
    cmd = [
        "uvicorn",
        "main:app",
        "--host", "0.0.0.0",
        "--port", "8000",
        "--workers", "6"
    ]
    
    os.execvp("uvicorn", cmd)

