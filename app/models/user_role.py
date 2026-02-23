import uuid

from sqlalchemy import ForeignKey, SmallInteger
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class UserRole(Base):
    __tablename__ = "user_roles"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )

    role_id: Mapped[int] = mapped_column(
        SmallInteger,
        ForeignKey("roles.id", ondelete="RESTRICT"),
        primary_key=True,
    )
