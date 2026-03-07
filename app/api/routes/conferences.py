import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.conference import ConferenceCreate, ConferenceResponse, ConferenceUpdate
from app.services import conference_service
from app.api.deps import get_current_user, require_admin

router = APIRouter(prefix="/conferences", tags=["conferences"])


@router.post("/", response_model=ConferenceResponse, dependencies=[Depends(require_admin)])
def create_conference(payload: ConferenceCreate, db: Session = Depends(get_db)):
    return conference_service.create_conference(db, payload)


@router.get("/", response_model=list[ConferenceResponse])
def list_conferences(is_active: bool | None = None, db: Session = Depends(get_db)):
    return conference_service.list_conferences(db, is_active)


@router.get("/{conference_id}", response_model=ConferenceResponse)
def get_conference(conference_id: uuid.UUID, db: Session = Depends(get_db)):
    conference = conference_service.get_conference(db, conference_id)
    if not conference:
        raise HTTPException(status_code=404, detail="Конференция не найдена")
    return conference


@router.patch("/{conference_id}", response_model=ConferenceResponse, dependencies=[Depends(require_admin)])
def update_conference(
    conference_id: uuid.UUID,
    payload: ConferenceUpdate,
    db: Session = Depends(get_db),
):
    conference = conference_service.get_conference(db, conference_id)
    if not conference:
        raise HTTPException(status_code=404, detail="Конференция не найдена")
    return conference_service.update_conference(db, conference, payload)


@router.delete("/{conference_id}", status_code=204, dependencies=[Depends(require_admin)])
def delete_conference(conference_id: uuid.UUID, db: Session = Depends(get_db)):
    conference = conference_service.get_conference(db, conference_id)
    if not conference:
        raise HTTPException(status_code=404, detail="Конференция не найдена")
    conference_service.delete_conference(db, conference)