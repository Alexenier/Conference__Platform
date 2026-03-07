import io
import uuid
from sqlalchemy.orm import Session, joinedload

from PyPDF2 import PdfMerger
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.lib.enums import TA_CENTER
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer

from app.models.submission import Submission
from app.models.submission_file import SubmissionFile
from app.models.conference import Conference
from app.services.storage import download_file
from app.schemas.submission import VALID_SECTIONS


def generate_collection_pdf(db: Session, conference_id: uuid.UUID) -> bytes:
    conference = db.query(Conference).filter(Conference.id == conference_id).first()
    if not conference:
        raise ValueError("Конференция не найдена")

    submissions = (
        db.query(Submission)
        .options(joinedload(Submission.authors))
        .filter(
            Submission.conference_id == conference_id,
            Submission.status == "accepted",
        )
        .all()
    )

    if not submissions:
        raise ValueError("Нет принятых заявок для формирования сборника")

    merger = PdfMerger()

    # Титульная страница
    title_pdf = _make_title_page(conference)
    merger.append(io.BytesIO(title_pdf))

    # Группируем по секциям
    by_section: dict[str, list[Submission]] = {}
    no_section: list[Submission] = []
    for s in submissions:
        if s.section:
            by_section.setdefault(s.section, []).append(s)
        else:
            no_section.append(s)
    if no_section:
        by_section["Без секції"] = no_section

    sections_order = VALID_SECTIONS + (["Без секції"] if no_section else [])

    for section_name in sections_order:
        section_submissions = by_section.get(section_name)
        if not section_submissions:
            continue

        # Страница-разделитель секции
        section_pdf = _make_section_page(section_name)
        merger.append(io.BytesIO(section_pdf))

        for sub in section_submissions:
            # Берём последний загруженный .docx файл
            file_record = (
                db.query(SubmissionFile)
                .filter(
                    SubmissionFile.submission_id == sub.id,
                    SubmissionFile.original_name.like("%.docx"),
                )
                .order_by(SubmissionFile.uploaded_at.desc())
                .first()
            )

            if not file_record:
                continue

            try:
                pdf_bytes = download_file(file_record.bucket, file_record.object_key)
                merger.append(io.BytesIO(pdf_bytes))
            except Exception:
                continue

    output = io.BytesIO()
    merger.write(output)
    merger.close()
    return output.getvalue()


def _make_title_page(conference: Conference) -> bytes:
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        leftMargin=20 * mm, rightMargin=20 * mm,
        topMargin=40 * mm, bottomMargin=20 * mm,
    )
    styles = getSampleStyleSheet()
    style_title = ParagraphStyle(
        "t", parent=styles["Normal"],
        fontSize=18, fontName="Helvetica-Bold",
        alignment=TA_CENTER, spaceAfter=10,
    )
    style_sub = ParagraphStyle(
        "s", parent=styles["Normal"],
        fontSize=13, fontName="Helvetica",
        alignment=TA_CENTER, spaceAfter=6,
    )
    story = [
        Spacer(1, 20 * mm),
        Paragraph(conference.title.upper(), style_title),
        Spacer(1, 10 * mm),
        Paragraph("ЗБІРНИК ТЕЗ ДОПОВІДЕЙ", style_sub),
        Paragraph(
            conference.submission_deadline.strftime("%d.%m.%Y"),
            style_sub,
        ),
    ]
    doc.build(story)
    return buffer.getvalue()


def _make_section_page(section_name: str) -> bytes:
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        leftMargin=20 * mm, rightMargin=20 * mm,
        topMargin=40 * mm, bottomMargin=20 * mm,
    )
    styles = getSampleStyleSheet()
    style = ParagraphStyle(
        "sec", parent=styles["Normal"],
        fontSize=15, fontName="Helvetica-Bold",
        alignment=TA_CENTER,
    )
    story = [
        Spacer(1, 30 * mm),
        Paragraph(f"СЕКЦІЯ", style),
        Spacer(1, 5 * mm),
        Paragraph(section_name.upper(), style),
    ]
    doc.build(story)
    return buffer.getvalue()