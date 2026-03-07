import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.submission import (
    SubmissionCreate, SubmissionResponse, SubmissionStatusUpdate, VALID_SECTIONS
)
from app.services import submission_service
from app.api.deps import get_current_user, require_org_committee, require_participant
from app.models.user import User

router = APIRouter(prefix="/submissions", tags=["submissions"])


@router.get("/sections")
def list_sections():
    return {"sections": VALID_SECTIONS}


@router.post("/", response_model=SubmissionResponse)
def create_submission(
    payload: SubmissionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_participant),
):
    if payload.section and payload.section not in VALID_SECTIONS:
        raise HTTPException(
            status_code=422,
            detail=f"Недопустима секція. Доступні: {VALID_SECTIONS}"
        )
    return submission_service.create_submission(db=db, payload=payload)


@router.get("/", response_model=list[SubmissionResponse])
def list_submissions(
    conference_id: uuid.UUID | None = None,
    status: str | None = None,
    section: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return submission_service.list_submissions(db, conference_id, status, section)


@router.get("/{submission_id}", response_model=SubmissionResponse)
def get_submission(
    submission_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    submission = submission_service.get_submission(db, submission_id)
    if not submission:
        raise HTTPException(status_code=404, detail="Submission не найден")
    return submission


@router.patch("/{submission_id}/status", response_model=SubmissionResponse)
def update_status(
    submission_id: uuid.UUID,
    payload: SubmissionStatusUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_org_committee),
):
    submission = submission_service.get_submission(db, submission_id)
    if not submission:
        raise HTTPException(status_code=404, detail="Submission не найден")
    try:
        return submission_service.update_status(db, submission, payload.status)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))