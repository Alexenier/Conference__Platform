from fastapi import FastAPI
from app.core.config import settings
from app.api.router import api_router

app = FastAPI(title=settings.app_name)
app.include_router(api_router)

@app.get("/health")
def health():
    return {"status": "ok", "app": settings.app_name}
