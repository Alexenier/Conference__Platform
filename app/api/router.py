from fastapi import APIRouter
from app.api.routes import files, submission_files

api_router = APIRouter()
api_router.include_router(files.router)
api_router.include_router(submission_files.router)