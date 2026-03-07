import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class ConferenceCreate(BaseModel):
    title: str
    description: Optional[str] = None
    submission_deadline: datetime


class ConferenceUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    submission_deadline: Optional[datetime] = None
    is_active: Optional[bool] = None


class ConferenceResponse(BaseModel):
    id: uuid.UUID
    title: str
    description: Optional[str]
    submission_deadline: datetime
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}