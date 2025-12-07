from fastapi import FastAPI
from datetime import datetime
from sqlalchemy import text
from config.db import engine
from database import init_db
from routes import router

init_db()

app = FastAPI(
    title="Gamification API",
    description="FastAPI + PostgreSQL с автоматическим созданием всех таблиц",
    version="0.1.0"
)

app.include_router(router)