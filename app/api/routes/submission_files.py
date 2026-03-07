import uuid
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.services.submission_file_service import (
    upload_submission_file,
    get_submission_files,
)

router = APIRouter(prefix="/submissions/{submission_id}/files", tags=["submission-files"])


@router.post("/")
async def upload_file(
    submission_id: uuid.UUID,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    try:
        record = upload_submission_file(
            db=db,
            submission_id=submission_id,
            fileobj=file.file,
            original_name=file.filename,
            content_type=file.content_type or "application/octet-stream",
            size_bytes=None,
        )
        return {
            "id": record.id,
            "submission_id": record.submission_id,
            "original_name": record.original_name,
            "object_key": record.object_key,
            "bucket": record.bucket,
            "uploaded_at": record.uploaded_at,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/")
def list_files(submission_id: uuid.UUID, db: Session = Depends(get_db)):
    files = get_submission_files(db, submission_id)
    return [
        {
            "id": f.id,
            "original_name": f.original_name,
            "object_key": f.object_key,
            "content_type": f.content_type,
            "size_bytes": f.size_bytes,
            "uploaded_at": f.uploaded_at,
        }
        for f in files
    ]