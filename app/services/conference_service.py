import uuid
from sqlalchemy.orm import Session
from app.models.conference import Conference
from app.schemas.conference import ConferenceCreate, ConferenceUpdate


def create_conference(db: Session, payload: ConferenceCreate) -> Conference:
    conference = Conference(
        title=payload.title,
        description=payload.description,
        submission_deadline=payload.submission_deadline,
    )
    db.add(conference)
    db.commit()
    db.refresh(conference)
    return conference


def get_conference(db: Session, conference_id: uuid.UUID) -> Conference | None:
    return db.query(Conference).filter(Conference.id == conference_id).first()


def list_conferences(db: Session, is_active: bool | None = None) -> list[Conference]:
    q = db.query(Conference)
    if is_active is not None:
        q = q.filter(Conference.is_active == is_active)
    return q.all()


def update_conference(db: Session, conference: Conference, payload: ConferenceUpdate) -> Conference:
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(conference, field, value)
    db.commit()
    db.refresh(conference)
    return conference


def delete_conference(db: Session, conference: Conference) -> None:
    db.delete(conference)
    db.commit()