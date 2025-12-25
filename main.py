import os

from fastapi import FastAPI
from routes import router

from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

app = FastAPI(
    title="Gamification API",
    description="FastAPI + PostgreSQL с автоматическим созданием всех таблиц",
    version="0.1.0"
)

app.include_router(router)

#Отдача статических файлов из папки assets
app.mount("/assets", StaticFiles(directory="frontend/dist/assets"), name="assets")

#Отдает конкретный файл если путь указывает на него или отдает index(React)
@app.get("/{full_path:path}")
async def serve_frontend(full_path: str = ""):
    if full_path and os.path.exists(f"frontend/dist/{full_path}"):
        return FileResponse(f"frontend/dist/{full_path}")

    return FileResponse("frontend/dist/index.html")

