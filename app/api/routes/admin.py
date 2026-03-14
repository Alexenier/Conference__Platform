from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
import uuid

from app.db.session import get_db
from app.schemas.auth import UserResponse
from app.api.deps import require_admin
from app.models.user import User
from app.models.user_role import UserRole
from app.core.security import hash_password

router = APIRouter(prefix="/admin", tags=["admin"])


class CreateUserRequest(BaseModel):
    email: str
    password: str
    full_name: Optional[str] = None
    role_id: int = 1  # по умолчанию participant


@router.post("/users", response_model=UserResponse, dependencies=[Depends(require_admin)])
def create_user(payload: CreateUserRequest, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.email == payload.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Користувач з таким email вже існує")

    user = User(
        email=payload.email,
        password_hash=hash_password(payload.password),
        full_name=payload.full_name,
    )
    db.add(user)
    db.flush()
    db.add(UserRole(user_id=user.id, role_id=payload.role_id))
    db.commit()
    db.refresh(user)
    return user


@router.get("/users", dependencies=[Depends(require_admin)])
def list_users(db: Session = Depends(get_db)):
    users = db.query(User).all()
    result = []
    for u in users:
        roles = db.query(UserRole).filter(UserRole.user_id == u.id).all()
        result.append({
            "id": u.id,
            "email": u.email,
            "full_name": u.full_name,
            "is_active": u.is_active,
            "role_ids": [r.role_id for r in roles],
        })
    return result


@router.delete("/users/{user_id}", dependencies=[Depends(require_admin)])
def delete_user(user_id: uuid.UUID, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Користувача не знайдено")
    db.delete(user)
    db.commit()
    return {"ok": True}