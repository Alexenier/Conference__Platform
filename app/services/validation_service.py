import io
import uuid
from sqlalchemy.orm import Session

from app.models.validation_report import ValidationReport
from app.services.thesis_validation.validator import validate_thesis_docx
from app.core.config import settings


def validate_and_save(
    db: Session,
    submission_file_id: uuid.UUID,
    file_bytes: bytes,
) -> ValidationReport:

    # Якщо є Anthropic API ключ — використовуємо AI валідатор
    if settings.anthropic_api_key:
        try:
            from app.services.ai_validator import validate_with_claude
            result = validate_with_claude(file_bytes, settings.anthropic_api_key)
            ok = result.get("ok", True)
            issues = result.get("issues", [])
        except Exception as e:
            print(f"[AI validation] fallback to basic: {e}")
            report = validate_thesis_docx(io.BytesIO(file_bytes))
            ok = report.ok
            issues = [i.to_dict() for i in report.issues]
    else:
        # Базовий валідатор
        report = validate_thesis_docx(io.BytesIO(file_bytes))
        ok = report.ok
        issues = [i.to_dict() for i in report.issues]

    record = ValidationReport(
        submission_file_id=submission_file_id,
        ok=ok,
        issues=issues,
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