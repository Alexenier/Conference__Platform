import uuid
from pydantic import BaseModel


class RoleResponse(BaseModel):
    id: int
    name: str

    model_config = {"from_attributes": True}


class UserRoleAssign(BaseModel):
    user_id: uuid.UUID
    role_id: int


class UserRolesResponse(BaseModel):
    user_id: uuid.UUID
    roles: list[RoleResponse]