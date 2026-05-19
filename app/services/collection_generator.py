"""
Генератор збірника тез конференції.
Алгоритм:
  1. Вибираємо всі прийняті заявки (status='accepted') з файлами .docx
  2. Завантажуємо кожен .docx з MinIO
  3. Конвертуємо .docx → .pdf через LibreOffice (headless)
  4. Генеруємо титульну сторінку через WeasyPrint
  5. Зливаємо всі PDF через PyPDF2
"""
import io
import os
import uuid
import subprocess
import tempfile
from pathlib import Path

from PyPDF2 import PdfMerger
from jinja2 import Environment, BaseLoader
from sqlalchemy.orm import Session, joinedload
import weasyprint

from app.models.submission import Submission
from app.models.submission_file import SubmissionFile
from app.models.conference import Conference
from app.services.storage import download_file
from app.schemas.submission import VALID_SECTIONS
from app.core.config import settings


# ---------------------------------------------------------------------------
# Конвертація .docx → PDF через LibreOffice
# ---------------------------------------------------------------------------

def _docx_to_pdf_bytes(docx_bytes: bytes) -> bytes | None:
    """
    Конвертує .docx (байти) у PDF (байти) через LibreOffice headless.
    Повертає None якщо конвертація не вдалась.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        input_path = Path(tmpdir) / "input.docx"
        output_path = Path(tmpdir) / "input.pdf"

        input_path.write_bytes(docx_bytes)

        try:
            result = subprocess.run(
                [
                    "libreoffice",
                    "--headless",
                    "--norestore",
                    "--convert-to", "pdf",
                    "--outdir", tmpdir,
                    str(input_path),
                ],
                timeout=60,
                capture_output=True,
                env={**os.environ, "HOME": tmpdir},
            )
            if result.returncode != 0:
                print(f"[LibreOffice] помилка: {result.stderr.decode()}")
                return None

            if not output_path.exists():
                print("[LibreOffice] PDF не створено")
                return None

            return output_path.read_bytes()

        except subprocess.TimeoutExpired:
            print("[LibreOffice] timeout")
            return None
        except FileNotFoundError:
            print("[LibreOffice] не встановлено")
            return None


# ---------------------------------------------------------------------------
# Титульна сторінка збірника
# ---------------------------------------------------------------------------

TITLE_TEMPLATE = """<!DOCTYPE html>
<html lang="uk">
<head>
<meta charset="utf-8">
<style>
  @font-face {
    font-family: 'TNR';
    src: url('/usr/share/fonts/truetype/liberation/LiberationSerif-Regular.ttf');
    font-weight: normal;
  }
  @font-face {
    font-family: 'TNR';
    src: url('/usr/share/fonts/truetype/liberation/LiberationSerif-Bold.ttf');
    font-weight: bold;
  }
  @page { size: A4; margin: 20mm; }
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body {
    font-family: 'TNR', serif;
    font-size: 12pt;
    text-align: center;
    padding-top: 40mm;
  }
  .ministry { font-size: 10pt; font-weight: bold; font-variant: small-caps; }
  .institution { font-size: 10pt; margin-top: 3mm; }
  .institution.bold { font-weight: bold; }
  .title { font-size: 18pt; font-weight: bold; text-transform: uppercase; margin-top: 20mm; line-height: 1.3; }
  .subtitle { font-size: 14pt; letter-spacing: 6px; margin-top: 10mm; }
  .date { font-size: 12pt; margin-top: 20mm; }
  .city { font-size: 12pt; margin-top: 30mm; }
</style>
</head>
<body>
  <p class="ministry">{{ ministry_text }}</p>
  {% if institution1_text %}
  <p class="institution">{{ institution1_text | replace('\n', '<br>') | safe }}</p>
  {% endif %}
  {% if institution2_text %}
  <p class="institution bold">{{ institution2_text | replace('\n', '<br>') | safe }}</p>
  {% endif %}
  <p class="title">{{ conference.title }}</p>
  <p class="subtitle">З Б І Р Н И К &nbsp; Т Е З</p>
  <p class="date">{{ date_formatted }}</p>
  <p class="city">{{ conference_city }} – {{ conference.submission_deadline.year }}</p>
</body>
</html>"""


def _fmt_date_uk(dt) -> str:
    months = [
        "січня", "лютого", "березня", "квітня", "травня", "червня",
        "липня", "серпня", "вересня", "жовтня", "листопада", "грудня",
    ]
    return f"{dt.day} {months[dt.month - 1]} {dt.year} р."


def _make_title_pdf(conference: Conference) -> bytes:
    env = Environment(loader=BaseLoader())
    html = env.from_string(TITLE_TEMPLATE).render(
        conference=conference,
        date_formatted=_fmt_date_uk(conference.submission_deadline),
        ministry_text=settings.ministry_text,
        institution1_text=settings.institution1_text,
        institution2_text=settings.institution2_text,
        conference_city=settings.conference_city,
    )
    return weasyprint.HTML(string=html).write_pdf()


# ---------------------------------------------------------------------------
# Розділювач секцій
# ---------------------------------------------------------------------------

SECTION_TEMPLATE = """<!DOCTYPE html>
<html lang="uk">
<head>
<meta charset="utf-8">
<style>
  @font-face {
    font-family: 'TNR';
    src: url('/usr/share/fonts/truetype/liberation/LiberationSerif-Bold.ttf');
    font-weight: bold;
  }
  @page { size: A4; margin: 20mm; }
  * { margin: 0; padding: 0; }
  body {
    font-family: 'TNR', serif;
    font-size: 14pt;
    font-weight: bold;
    text-align: center;
    padding-top: 60mm;
    text-transform: uppercase;
  }
  .label { font-size: 12pt; font-weight: normal; margin-bottom: 6mm; }
</style>
</head>
<body>
  <p class="label">СЕКЦІЯ</p>
  <p>{{ section_name }}</p>
</body>
</html>"""


def _make_section_pdf(section_name: str) -> bytes:
    env = Environment(loader=BaseLoader())
    html = env.from_string(SECTION_TEMPLATE).render(section_name=section_name)
    return weasyprint.HTML(string=html).write_pdf()


# ---------------------------------------------------------------------------
# Головна функція
# ---------------------------------------------------------------------------

def generate_collection_pdf(db: Session, conference_id: uuid.UUID) -> bytes:
    conference = db.query(Conference).filter(Conference.id == conference_id).first()
    if not conference:
        raise ValueError("Конференцію не знайдено")

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
        raise ValueError("Немає прийнятих заявок для формування збірника")

    # Групуємо по секціях
    by_section: dict[str, list[Submission]] = {}
    no_section: list[Submission] = []
    for s in submissions:
        if s.section:
            by_section.setdefault(s.section, []).append(s)
        else:
            no_section.append(s)
    if no_section:
        by_section["Без секції"] = no_section

    order = [s for s in VALID_SECTIONS if s in by_section]
    if "Без секції" in by_section:
        order.append("Без секції")

    merger = PdfMerger()

    # Титульна сторінка
    merger.append(io.BytesIO(_make_title_pdf(conference)))

    converted = 0
    failed = 0

    for section_name in order:
        section_submissions = by_section.get(section_name)
        if not section_submissions:
            continue

        # Розділювач секції
        merger.append(io.BytesIO(_make_section_pdf(section_name)))

        for sub in sorted(section_submissions, key=lambda s: (s.submitted_at is None, s.submitted_at)):
            # Беремо останній завантажений .docx
            file_record = (
                db.query(SubmissionFile)
                .filter(
                    SubmissionFile.submission_id == sub.id,
                    SubmissionFile.original_name.ilike("%.docx"),
                )
                .order_by(SubmissionFile.uploaded_at.desc())
                .first()
            )

            if not file_record:
                print(f"[collection] немає файлу для '{sub.title}'")
                failed += 1
                continue

            try:
                docx_bytes = download_file(file_record.bucket, file_record.object_key)
                pdf_bytes = _docx_to_pdf_bytes(docx_bytes)
                if pdf_bytes:
                    merger.append(io.BytesIO(pdf_bytes))
                    converted += 1
                else:
                    failed += 1
            except Exception as e:
                print(f"[collection] помилка для '{sub.title}': {e}")
                failed += 1

    print(f"[collection] конвертовано: {converted}, пропущено: {failed}")

    output = io.BytesIO()
    merger.write(output)
    merger.close()
    return output.getvalue()