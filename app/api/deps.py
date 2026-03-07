from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.security import decode_access_token
from app.db.session import get_db
from app.models.user import User
from app.models.user_role import UserRole

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    payload = decode_access_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Недействительный токен",
            headers={"WWW-Authenticate": "Bearer"},
        )
    user = db.query(User).filter(User.id == payload.get("sub")).first()
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Пользователь не найден или неактивен",
        )
    return user


def get_user_roles(db: Session, user_id) -> list[int]:
    rows = db.query(UserRole).filter(UserRole.user_id == user_id).all()
    return [r.role_id for r in rows]


def require_roles(*role_ids: int):
    """
    Роли:
      1 = participant
      2 = org_committee
      3 = admin
    """
    def checker(
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db),
    ) -> User:
        user_roles = get_user_roles(db, current_user.id)
        if not any(r in user_roles for r in role_ids):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Недостаточно прав",
            )
        return current_user
    return checker


# Готовые dependency для использования в роутерах
require_admin = require_roles(3)
require_org_committee = require_roles(2, 3)  # org_committee или admin
require_participant = require_roles(1, 2, 3)  # любой авторизованный с ролью