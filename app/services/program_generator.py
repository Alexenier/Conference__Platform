"""
Генератор програми конференції.
Використовує WeasyPrint (HTML→PDF) + Jinja2 шаблони.
Шаблон: app/templates/program.html
"""
import uuid
from dataclasses import dataclass, field
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape
from sqlalchemy.orm import Session, joinedload
import weasyprint

from app.models.submission import Submission
from app.models.conference import Conference
from app.schemas.submission import VALID_SECTIONS
from app.core.config import settings

TEMPLATES_DIR = Path(__file__).parent.parent / "templates"


# ---------------------------------------------------------------------------
# Dataclasses для передачі в шаблон
# ---------------------------------------------------------------------------

@dataclass
class HeadPerson:
    rank: str   # "к. ф-м. н., доцент"
    name: str   # "Пенко Валерій Георгійович"


@dataclass
class SectionData:
    name: str
    heads: list = field(default_factory=list)
    secretary: object = None
    location: str = ""
    submissions: list = field(default_factory=list)


@dataclass
class SubmissionData:
    title: str
    authors_str: str


# ---------------------------------------------------------------------------
# Допоміжні
# ---------------------------------------------------------------------------

def _fmt_date_uk(dt) -> str:
    months = [
        "січня", "лютого", "березня", "квітня", "травня", "червня",
        "липня", "серпня", "вересня", "жовтня", "листопада", "грудня",
    ]
    return f"{dt.day} {months[dt.month - 1]} {dt.year} р."


def _authors_str(submission: Submission) -> str:
    if not submission.authors:
        return ""
    return ", ".join(
        a.full_name for a in sorted(submission.authors, key=lambda a: a.order)
    )


def _parse_head(head_str: str) -> HeadPerson:
    """
    'к. ф-м. н., доцент Пенко Валерій Георгійович'
    → HeadPerson(rank='к. ф-м. н., доцент', name='Пенко Валерій Георгійович')
    """
    parts = head_str.split()
    rank_parts, name_parts = [], []
    found_name = False

    for word in parts:
        if not found_name:
            clean = word.rstrip(',')
            if clean[0].isupper() and not clean.endswith('.') and rank_parts:
                found_name = True
                name_parts.append(word)
            else:
                rank_parts.append(word)
        else:
            name_parts.append(word)

    rank = " ".join(rank_parts).rstrip(',').strip()
    name = " ".join(name_parts).strip()
    return HeadPerson(rank=rank, name=name) if name else HeadPerson(rank="", name=head_str)


def _build_sections(submissions, section_configs, default_location) -> list:
    by_section: dict[str, list] = {}
    no_section = []

    for sub in submissions:
        if sub.section:
            by_section.setdefault(sub.section, []).append(sub)
        else:
            no_section.append(sub)

    if no_section:
        by_section["Без секції"] = no_section

    order = [s for s in VALID_SECTIONS if s in by_section]
    if "Без секції" in by_section:
        order.append("Без секції")

    result = []
    for section_name in order:
        subs = sorted(
            by_section[section_name],
            key=lambda s: (s.submitted_at is None, s.submitted_at),
        )
        cfg = section_configs.get(section_name, {})

        result.append(SectionData(
            name=section_name,
            heads=[_parse_head(h) for h in cfg.get("heads", [])],
            secretary=_parse_head(cfg["secretary"]) if cfg.get("secretary") else None,
            location=cfg.get("location", default_location),
            submissions=[
                SubmissionData(title=s.title, authors_str=_authors_str(s))
                for s in subs
            ],
        ))

    return result


# ---------------------------------------------------------------------------
# Головна функція
# ---------------------------------------------------------------------------

def generate_program_pdf(db: Session, conference_id: uuid.UUID) -> bytes:
    conference = db.query(Conference).filter(Conference.id == conference_id).first()
    if not conference:
        raise ValueError("Конференція не знайдена")

    submissions = (
        db.query(Submission)
        .options(joinedload(Submission.authors))
        .filter(
            Submission.conference_id == conference_id,
            Submission.status == "accepted",
        )
        .all()
    )

    sections = _build_sections(
        submissions=submissions,
        section_configs=settings.section_configs,
        default_location=settings.conference_location,
    )

    env = Environment(
        loader=FileSystemLoader(str(TEMPLATES_DIR)),
        autoescape=select_autoescape(["html"]),
    )
    html = env.get_template("program.html").render(
        conference=conference,
        sections=sections,
        date_formatted=_fmt_date_uk(conference.submission_deadline),
        ministry_text=settings.ministry_text,
        institution1_text=settings.institution1_text,
        institution2_text=settings.institution2_text,
        conference_city=settings.conference_city,
    )

    return weasyprint.HTML(string=html).write_pdf()