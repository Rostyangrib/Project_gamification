import uvicorn

if __name__ == "__main__":
    print("Запуск FastAPI сервера в режиме разработки...")
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        workers=1
    )