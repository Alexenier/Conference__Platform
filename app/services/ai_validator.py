"""
AI-валідатор тез через Anthropic Claude API.
Перед зверненням до моделі вимірює параметри форматування документа
(шрифт, поля, відступи, інтервали) засобами python-docx та передає їх
моделі як вихідні дані. Модель формує підсумкові рекомендації на основі
точно виміряних параметрів та семантичного аналізу тексту.
Використовується якщо в .env задано ANTHROPIC_API_KEY.
"""
import json
import io
import urllib.request
import urllib.error

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Length

# --- Вимоги до оформлення ---
REQUIRED_FONT = "Times New Roman"
REQUIRED_SIZE_PT = 14.0
MM_TO_INCH = 1 / 25.4
TWIPS_PER_INCH = 1440
MARGIN_20MM_TWIPS = int(round(20 * MM_TO_INCH * TWIPS_PER_INCH))   # ~1134
INDENT_125CM_TWIPS = int(round(12.5 * MM_TO_INCH * TWIPS_PER_INCH))  # ~709
LINE_SPACING_TARGET = 1.15


def _extract_text(doc: Document) -> str:
    paragraphs = [p.text.strip() for p in doc.paragraphs if p.text.strip()]
    return "\n".join(paragraphs)


def _measure_format(doc: Document) -> dict:
    """Вимірює фактичні параметри форматування документа."""
    result = {}

    # --- Поля сторінки (беремо першу секцію) ---
    if doc.sections:
        s = doc.sections[0]
        result["margins_mm"] = {
            "top": round(s.top_margin.mm, 1),
            "bottom": round(s.bottom_margin.mm, 1),
            "left": round(s.left_margin.mm, 1),
            "right": round(s.right_margin.mm, 1),
        }

    paragraphs = [p for p in doc.paragraphs if (p.text or "").strip()]

    # --- Шрифт та розмір основного тексту (по body, після 3 рядків шапки) ---
    body = paragraphs[3:] if len(paragraphs) > 3 else paragraphs
    fonts = set()
    sizes = set()
    for p in body[:30]:
        for r in p.runs:
            if not (r.text or "").strip():
                continue
            if r.font.name:
                fonts.add(r.font.name)
            if r.font.size:
                sizes.add(round(r.font.size.pt, 1))
    result["body_fonts"] = sorted(fonts) if fonts else ["(не визначено, задано стилем)"]
    result["body_sizes_pt"] = sorted(sizes) if sizes else ["(не визначено, задано стилем)"]

    # --- Курсив авторів (другий рядок шапки) ---
    if len(paragraphs) >= 2:
        authors_p = paragraphs[1]
        italic_runs = [r.italic for r in authors_p.runs if (r.text or "").strip()]
        if italic_runs and all(v is True for v in italic_runs):
            result["authors_italic"] = True
        elif italic_runs:
            result["authors_italic"] = False
        else:
            result["authors_italic"] = None

    # --- Великі літери у назві (перший рядок) ---
    if paragraphs:
        title = (paragraphs[0].text or "").strip()
        result["title_is_uppercase"] = (title == title.upper() and bool(title))

    # --- Міжрядковий інтервал та абзацний відступ (по body) ---
    spacings = set()
    indents_mm = set()
    for p in body[:30]:
        ls = p.paragraph_format.line_spacing
        if isinstance(ls, (int, float)):
            spacings.add(round(float(ls), 2))
        ind = p.paragraph_format.first_line_indent
        if ind is not None:
            try:
                indents_mm.add(round(ind.mm, 1))
            except Exception:
                pass
    result["line_spacings"] = sorted(spacings) if spacings else ["(не визначено)"]
    result["first_line_indents_mm"] = sorted(indents_mm) if indents_mm else ["(не визначено)"]

    return result


def _format_requirements_block(fmt: dict) -> str:
    """Формує текстовий блок з виміряними параметрами для промпту."""
    lines = ["ВИМІРЯНІ ПАРАМЕТРИ ФОРМАТУВАННЯ (отримані програмно з .docx):"]
    if "margins_mm" in fmt:
        m = fmt["margins_mm"]
        lines.append(f"- Поля сторінки (мм): верхнє {m['top']}, нижнє {m['bottom']}, "
                     f"ліве {m['left']}, праве {m['right']} (вимога: 20 мм з усіх боків)")
    lines.append(f"- Шрифт основного тексту: {fmt.get('body_fonts')} (вимога: {REQUIRED_FONT})")
    lines.append(f"- Розмір основного тексту (pt): {fmt.get('body_sizes_pt')} (вимога: {REQUIRED_SIZE_PT})")
    lines.append(f"- Міжрядковий інтервал: {fmt.get('line_spacings')} (вимога: {LINE_SPACING_TARGET})")
    lines.append(f"- Абзацний відступ першого рядка (мм): {fmt.get('first_line_indents_mm')} (вимога: 12.5 мм)")
    ai = fmt.get("authors_italic")
    ai_str = "так" if ai is True else ("ні" if ai is False else "не визначено")
    lines.append(f"- Автори оформлені курсивом: {ai_str} (вимога: так)")
    tu = fmt.get("title_is_uppercase")
    lines.append(f"- Назва великими літерами: {'так' if tu else 'ні'} (вимога: так)")
    return "\n".join(lines)


def validate_with_claude(file_bytes: bytes, api_key: str) -> dict:
    """
    Аналізує тези через Claude на основі тексту та виміряних параметрів форматування.
    Повертає: {"ok": True, "issues": [{"message": "..."}]}
    """
    doc = Document(io.BytesIO(file_bytes))
    text = _extract_text(doc)

    if len(text) < 100:
        return {"ok": True, "issues": [{"message": "Документ занадто короткий для аналізу."}]}

    fmt = _measure_format(doc)
    format_block = _format_requirements_block(fmt)
    text_excerpt = text[:12000]

    prompt = f"""Ти перевіряєш оформлення наукових тез для академічної конференції.
Твоя задача — на основі НАДАНИХ ДАНИХ скласти перелік конкретних зауважень.

ВАЖЛИВІ ПРАВИЛА:
- Параметри форматування (шрифт, поля, відступи, інтервали, курсив, великі літери)
  вже ВИМІРЯНІ програмно і наведені нижче. Спирайся ВИКЛЮЧНО на ці виміряні значення,
  не роби припущень про форматування з тексту.
- Зміст (завершеність тексту, наявність списку літератури, структуру) оцінюй за текстом.
- Якщо текст завершується списком літератури — він НЕ є обірваним.
- НЕ вигадуй зауваження. Якщо за наданими даними все коректно — повертай порожній список.

{format_block}

ПЕРЕВІР ТА ВКАЖИ ЗАУВАЖЕННЯ (лише там, де є реальна невідповідність):
1. Форматування — порівняй виміряні значення з вимогами вище.
2. Структура тексту — чи є назва, автори, організація, основний текст.
3. Список літератури — чи присутній блок "Література"/"Список літератури" з нумерованими джерелами.
4. Завершеність — чи не обривається текст на середині думки.
5. Обсяг — чи відповідає повноцінним тезам (орієнтовно 1-2 сторінки).

Відповідай ТІЛЬКИ у форматі JSON, без жодного іншого тексту:
{{"issues": ["зауваження 1", "зауваження 2"]}}
Якщо зауважень немає — повертай: {{"issues": []}}

ТЕКСТ ТЕЗ:
{text_excerpt}"""

    request_body = json.dumps({
        "model": "claude-haiku-4-5",
        "max_tokens": 1024,
        "temperature": 0.0,
        "messages": [{"role": "user", "content": prompt}],
    }).encode("utf-8")

    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages",
        data=request_body,
        headers={
            "Content-Type": "application/json",
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            data = json.loads(response.read().decode("utf-8"))

        raw_text = ""
        for block in data.get("content", []):
            if block.get("type") == "text":
                raw_text += block.get("text", "")
        raw_text = raw_text.strip()

        if raw_text.startswith("```"):
            raw_text = raw_text.split("```")[1]
            if raw_text.startswith("json"):
                raw_text = raw_text[4:]
        raw_text = raw_text.strip()

        parsed = json.loads(raw_text)
        issues = [{"message": msg} for msg in parsed.get("issues", [])]
        return {"ok": True, "issues": issues}

    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        print(f"[Claude] HTTP {e.code}: {body}")
        return {"ok": True, "issues": []}
    except Exception as e:
        print(f"[Claude] помилка: {e}")
        return {"ok": True, "issues": []}