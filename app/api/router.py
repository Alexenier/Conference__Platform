from fastapi import APIRouter
from app.api.routes import auth, files, submission_files, submissions, conferences, roles

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(roles.router)
api_router.include_router(files.router)
api_router.include_router(submission_files.router)
api_router.include_router(submissions.router)
api_router.include_router(conferences.router)