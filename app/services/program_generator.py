import io
import uuid
from sqlalchemy.orm import Session, joinedload

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.enums import TA_CENTER, TA_LEFT

from app.models.submission import Submission
from app.models.conference import Conference
from app.schemas.submission import VALID_SECTIONS


def _register_fonts():
    try:
        pdfmetrics.registerFont(TTFont("DejaVu", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"))
        pdfmetrics.registerFont(TTFont("DejaVu-Bold", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"))
        pdfmetrics.registerFont(TTFont("DejaVu-Italic", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Oblique.ttf"))
        return "DejaVu", "DejaVu-Bold", "DejaVu-Italic"
    except Exception:
        return "Helvetica", "Helvetica-Bold", "Helvetica-Oblique"


def generate_program_pdf(db: Session, conference_id: uuid.UUID) -> bytes:
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

    font_normal, font_bold, font_italic = _register_fonts()

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=20 * mm,
        rightMargin=20 * mm,
        topMargin=20 * mm,
        bottomMargin=20 * mm,
    )

    styles = getSampleStyleSheet()

    style_title = ParagraphStyle(
        "title", parent=styles["Normal"],
        fontSize=16, fontName=font_bold,
        alignment=TA_CENTER, spaceAfter=6,
    )
    style_subtitle = ParagraphStyle(
        "subtitle", parent=styles["Normal"],
        fontSize=12, fontName=font_normal,
        alignment=TA_CENTER, spaceAfter=4,
    )
    style_section = ParagraphStyle(
        "section", parent=styles["Normal"],
        fontSize=13, fontName=font_bold,
        alignment=TA_CENTER, spaceBefore=12, spaceAfter=6,
    )
    style_report_title = ParagraphStyle(
        "report_title", parent=styles["Normal"],
        fontSize=11, fontName=font_bold,
        alignment=TA_LEFT, spaceAfter=2,
    )
    style_authors = ParagraphStyle(
        "authors", parent=styles["Normal"],
        fontSize=10, fontName=font_italic,
        alignment=TA_LEFT, spaceAfter=8,
    )

    story = []

    story.append(Paragraph(conference.title.upper(), style_title))
    story.append(Paragraph("ПРОГРАМА КОНФЕРЕНЦІЇ", style_subtitle))
    story.append(Paragraph(
        conference.submission_deadline.strftime("%d.%m.%Y"),
        style_subtitle,
    ))
    story.append(Spacer(1, 10 * mm))

    if not submissions:
        story.append(Paragraph("Прийнятих доповідей не знайдено.", styles["Normal"]))
    else:
        by_section: dict[str, list[Submission]] = {}
        no_section: list[Submission] = []

        for s in submissions:
            if s.section:
                by_section.setdefault(s.section, []).append(s)
            else:
                no_section.append(s)

        sections_order = VALID_SECTIONS + (["Без секції"] if no_section else [])
        if no_section:
            by_section["Без секції"] = no_section

        for section_name in sections_order:
            section_submissions = by_section.get(section_name)
            if not section_submissions:
                continue

            story.append(Paragraph(f"СЕКЦІЯ – {section_name.upper()}", style_section))
            story.append(Spacer(1, 3 * mm))

            for i, sub in enumerate(section_submissions, start=1):
                authors_sorted = sorted(sub.authors, key=lambda a: a.order)
                authors_str = ", ".join(a.full_name for a in authors_sorted) if authors_sorted else "Автор не вказаний"
                story.append(Paragraph(f"{i}. {sub.title.upper()}", style_report_title))
                story.append(Paragraph(authors_str, style_authors))

    doc.build(story)
    return buffer.getvalue()