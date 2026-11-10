from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr

from src.core.types import Role


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr
    name: str
    role: Role
    created_at: datetime


class RoleUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    role: Role
