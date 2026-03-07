from fastapi import APIRouter
from app.api.routes import files, submission_files, submissions, conferences

api_router = APIRouter()
api_router.include_router(files.router)
api_router.include_router(submission_files.router)
api_router.include_router(submissions.router)
api_router.include_router(conferences.router)