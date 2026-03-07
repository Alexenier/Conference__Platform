import uuid
from sqlalchemy.orm import Session

from app.models.submission_file import SubmissionFile
from app.core.config import settings
from app.services.storage import ensure_bucket_exists, upload_stream


def upload_submission_file(
    db: Session,
    submission_id: uuid.UUID,
    fileobj,
    original_name: str,
    content_type: str,
    size_bytes: int | None = None,
) -> SubmissionFile:
    ensure_bucket_exists(settings.s3_bucket)

    # читаем байты для валидации и загрузки
    file_bytes = fileobj.read()

    import io
    object_key = upload_stream(
        fileobj=io.BytesIO(file_bytes),
        original_name=original_name,
        content_type=content_type,
    )

    record = SubmissionFile(
        submission_id=submission_id,
        bucket=settings.s3_bucket,
        object_key=object_key,
        original_name=original_name,
        content_type=content_type,
        size_bytes=size_bytes or len(file_bytes),
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record, file_bytes


def get_submission_files(db: Session, submission_id: uuid.UUID) -> list[SubmissionFile]:
    return (
        db.query(SubmissionFile)
        .filter(SubmissionFile.submission_id == submission_id)
        .all()
    )


def delete_submission_file(db: Session, file_id: uuid.UUID) -> None:
    from app.services.storage import delete_file
    record = db.query(SubmissionFile).filter(SubmissionFile.id == file_id).first()
    if not record:
        raise ValueError("Файл не найден")

    try:
        delete_file(record.bucket, record.object_key)
    except Exception:
        pass  # если в MinIO уже нет — всё равно удаляем из БД

    db.delete(record)
    db.commit()