import uuid
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.services.submission_file_service import upload_submission_file, get_submission_files
from app.services.validation_service import validate_and_save, get_report
from app.api.deps import get_current_user

router = APIRouter(prefix="/submissions/{submission_id}/files", tags=["submission-files"])

DOCX_CONTENT_TYPE = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


@router.post("/")
async def upload_file(
    submission_id: uuid.UUID,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    try:
        record, file_bytes = upload_submission_file(
            db=db,
            submission_id=submission_id,
            fileobj=file.file,
            original_name=file.filename,
            content_type=file.content_type or "application/octet-stream",
        )

        validation = None
        is_docx = (
            file.content_type == DOCX_CONTENT_TYPE
            or (file.filename or "").endswith(".docx")
        )
        if is_docx:
            try:
                val_record = validate_and_save(db, record.id, file_bytes)
                validation = {"ok": val_record.ok, "issues": val_record.issues}
            except Exception as val_err:
                validation = {"ok": None, "error": str(val_err)}

        return {
            "id": record.id,
            "submission_id": record.submission_id,
            "original_name": record.original_name,
            "object_key": record.object_key,
            "bucket": record.bucket,
            "size_bytes": record.size_bytes,
            "uploaded_at": record.uploaded_at,
            "validation": validation,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/")
def list_files(
    submission_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
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


@router.get("/{file_id}/validation")
def get_validation(
    submission_id: uuid.UUID,
    file_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    report = get_report(db, file_id)
    if not report:
        raise HTTPException(status_code=404, detail="Отчёт валидации не найден")
    return {"ok": report.ok, "issues": report.issues, "created_at": report.created_at}

@router.delete("/{file_id}")
def delete_file(
    submission_id: uuid.UUID,
    file_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    from app.services.submission_file_service import delete_submission_file
    try:
        delete_submission_file(db, file_id)
        return {"ok": True}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))