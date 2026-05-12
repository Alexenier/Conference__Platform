from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.api.deps import get_current_user, get_user_roles
from app.services.search_service import search_submissions
from app.services.submission_service import get_submission
import uuid

router = APIRouter(prefix="/search", tags=["search"])


@router.get("/submissions")
def search(
    q: str = Query(..., min_length=1, description="Пошуковий запит"),
    conference_id: uuid.UUID | None = None,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    role_ids = get_user_roles(db, current_user.id)

    # Шукаємо ID в Elasticsearch
    ids = search_submissions(
        query=q,
        conference_id=str(conference_id) if conference_id else None
    )

    if not ids:
        return []

    # Фільтруємо по ролі — учасник бачить тільки свої
    results = []
    for submission_id in ids:
        submission = get_submission(db, uuid.UUID(submission_id))
        if not submission:
            continue
        if 2 not in role_ids and 3 not in role_ids:
            if str(submission.author_id) != str(current_user.id):
                continue
        results.append(submission)

    return results