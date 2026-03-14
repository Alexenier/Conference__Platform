import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.role import RoleResponse, UserRoleAssign, UserRolesResponse
from app.services import role_service
from app.api.deps import require_admin, get_current_user, get_user_roles as _get_user_role_ids
from app.models.user import User

router = APIRouter(prefix="/roles", tags=["roles"])


@router.get("/", response_model=list[RoleResponse])
def list_roles(db: Session = Depends(get_db)):
    return role_service.list_roles(db)


@router.get("/users/{user_id}", response_model=UserRolesResponse)
def get_user_roles(
    user_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    user_role_ids = _get_user_role_ids(db, current_user.id)
    if current_user.id != user_id and 3 not in user_role_ids:
        raise HTTPException(status_code=403, detail="Недостатньо прав")

    roles = role_service.get_user_roles(db, user_id)
    return UserRolesResponse(user_id=user_id, roles=roles)


@router.post("/assign", dependencies=[Depends(require_admin)])
def assign_role(payload: UserRoleAssign, db: Session = Depends(get_db)):
    try:
        role_service.assign_role(db, payload.user_id, payload.role_id)
        return {"ok": True, "user_id": payload.user_id, "role_id": payload.role_id}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/revoke", dependencies=[Depends(require_admin)])
def revoke_role(payload: UserRoleAssign, db: Session = Depends(get_db)):
    try:
        role_service.revoke_role(db, payload.user_id, payload.role_id)
        return {"ok": True, "user_id": payload.user_id, "role_id": payload.role_id}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))