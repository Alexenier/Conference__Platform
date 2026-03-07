import uuid
from sqlalchemy.orm import Session
from app.models.role import Role
from app.models.user import User
from app.models.user_role import UserRole


def list_roles(db: Session) -> list[Role]:
    return db.query(Role).all()


def get_user_roles(db: Session, user_id: uuid.UUID) -> list[Role]:
    rows = db.query(UserRole).filter(UserRole.user_id == user_id).all()
    role_ids = [r.role_id for r in rows]
    return db.query(Role).filter(Role.id.in_(role_ids)).all()


def assign_role(db: Session, user_id: uuid.UUID, role_id: int) -> None:
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise ValueError("Пользователь не найден")

    role = db.query(Role).filter(Role.id == role_id).first()
    if not role:
        raise ValueError("Роль не найдена")

    existing = db.query(UserRole).filter(
        UserRole.user_id == user_id,
        UserRole.role_id == role_id,
    ).first()
    if existing:
        return  # уже есть — ничего не делаем

    db.add(UserRole(user_id=user_id, role_id=role_id))
    db.commit()


def revoke_role(db: Session, user_id: uuid.UUID, role_id: int) -> None:
    row = db.query(UserRole).filter(
        UserRole.user_id == user_id,
        UserRole.role_id == role_id,
    ).first()
    if not row:
        raise ValueError("У пользователя нет такой роли")

    db.delete(row)
    db.commit()