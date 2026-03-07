import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel


VALID_SECTIONS = [
    "Інтелектуальні системи",
    "Сучасні інформаційні технології",
    "Методика викладання інформатики та ІКТ в освіті",
    "Моделювання та інформаційні технології",
]


class SubmissionAuthorCreate(BaseModel):
    full_name: str
    organization: Optional[str] = None
    email: Optional[str] = None
    is_presenter: bool = False
    order: int = 0


class SubmissionAuthorResponse(BaseModel):
    id: uuid.UUID
    full_name: str
    organization: Optional[str]
    email: Optional[str]
    is_presenter: bool
    order: int

    model_config = {"from_attributes": True}


class SubmissionCreate(BaseModel):
    conference_id: uuid.UUID
    author_id: uuid.UUID
    title: str
    abstract: Optional[str] = None
    section: Optional[str] = None
    authors: list[SubmissionAuthorCreate] = []


class SubmissionStatusUpdate(BaseModel):
    status: str


class SubmissionResponse(BaseModel):
    id: uuid.UUID
    conference_id: uuid.UUID
    author_id: uuid.UUID
    title: str
    abstract: Optional[str]
    section: Optional[str]
    status: str
    submitted_at: Optional[datetime]
    created_at: datetime
    authors: list[SubmissionAuthorResponse] = []

    model_config = {"from_attributes": True}