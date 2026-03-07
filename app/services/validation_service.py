import io
import uuid
from sqlalchemy.orm import Session

from app.models.validation_report import ValidationReport
from app.services.thesis_validation.validator import validate_thesis_docx


def validate_and_save(
    db: Session,
    submission_file_id: uuid.UUID,
    file_bytes: bytes,
) -> ValidationReport:
    # запускаем валидатор из байтов
    report = validate_thesis_docx(io.BytesIO(file_bytes))

    record = ValidationReport(
        submission_file_id=submission_file_id,
        ok=report.ok,
        issues=[i.to_dict() for i in report.issues],
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


def get_report(db: Session, submission_file_id: uuid.UUID) -> ValidationReport | None:
    return (
        db.query(ValidationReport)
        .filter(ValidationReport.submission_file_id == submission_file_id)
        .first()
    )