import uuid
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
import io

from app.db.session import get_db
from app.schemas.conference import ConferenceCreate, ConferenceResponse, ConferenceUpdate
from app.services import conference_service
from app.services.program_generator import generate_program_pdf
from app.api.deps import require_admin, get_current_user

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


@router.get("/{conference_id}/program.pdf", dependencies=[Depends(get_current_user)])
def download_program(conference_id: uuid.UUID, db: Session = Depends(get_db)):
    try:
        pdf_bytes = generate_program_pdf(db, conference_id)
        return StreamingResponse(
            io.BytesIO(pdf_bytes),
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename=program_{conference_id}.pdf"},
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    

@router.get("/{conference_id}/collection.pdf", dependencies=[Depends(require_admin)])
def download_collection(conference_id: uuid.UUID, db: Session = Depends(get_db)):
    try:
        from app.services.collection_generator import generate_collection_pdf
        pdf_bytes = generate_collection_pdf(db, conference_id)
        return StreamingResponse(
            io.BytesIO(pdf_bytes),
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename=collection_{conference_id}.pdf"},
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))