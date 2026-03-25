import uuid
from datetime import datetime
from sqlalchemy.orm import Session, joinedload

from app.models.submission import Submission
from app.models.submission_author import SubmissionAuthor
from app.schemas.submission import SubmissionCreate


VALID_TRANSITIONS = {
    "draft": ["submitted"],
    "submitted": ["under_review", "draft"],
    "under_review": ["accepted", "rejected"],
    "accepted": [],
    "rejected": ["draft"],
}


def create_submission(db: Session, payload: SubmissionCreate) -> Submission:
    submission = Submission(
        conference_id=payload.conference_id,
        author_id=payload.author_id,
        title=payload.title,
        abstract=payload.abstract,
        section=payload.section,
    )
    db.add(submission)
    db.flush()

    for author_data in payload.authors:
        author = SubmissionAuthor(
            submission_id=submission.id,
            full_name=author_data.full_name,
            organization=author_data.organization,
            email=author_data.email,
            is_presenter=author_data.is_presenter,
            order=author_data.order,
        )
        db.add(author)

    db.commit()
    db.refresh(submission)
    return submission


def get_submission(db: Session, submission_id: uuid.UUID) -> Submission | None:
    return (
        db.query(Submission)
        .options(joinedload(Submission.authors))
        .filter(Submission.id == submission_id)
        .first()
    )


def list_submissions(
    db: Session,
    conference_id: uuid.UUID | None = None,
    status: str | None = None,
    section: str | None = None,
    current_user_id=None,
    role_ids: list[int] = [],
) -> list[Submission]:
    q = db.query(Submission).options(joinedload(Submission.authors))

    # Тільки participant (1) — бачить лише свої заявки
    if current_user_id and 2 not in role_ids and 3 not in role_ids:
        q = q.filter(Submission.author_id == current_user_id)

    if conference_id:
        q = q.filter(Submission.conference_id == conference_id)
    if status:
        q = q.filter(Submission.status == status)
    if section:
        q = q.filter(Submission.section == section)
    return q.all()


def update_status(db: Session, submission: Submission, new_status: str) -> Submission:
    allowed = VALID_TRANSITIONS.get(submission.status, [])
    if new_status not in allowed:
        raise ValueError(
            f"Переход {submission.status} → {new_status} недопустим. Разрешено: {allowed}"
        )
    submission.status = new_status
    if new_status == "submitted":
        submission.submitted_at = datetime.utcnow()

    db.commit()
    db.refresh(submission)
    return submission