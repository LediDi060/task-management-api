from typing import Annotated

from fastapi import APIRouter, Depends

from src.api.dependencies import Limit, ObjectId, Offset, RoleChecker, get_user_service
from src.api.schemas.user import RoleUpdate, UserResponse
from src.core.types import Role
from src.services.user_service import UserService

router = APIRouter(
    prefix="/admin/users", tags=["admin"], dependencies=[Depends(RoleChecker([Role.ADMIN]))]
)


@router.get("", response_model=list[UserResponse])
async def list_users(
    service: Annotated[UserService, Depends(get_user_service)],
    offset: Offset = 0,
    limit: Limit = 20,
):
    return await service.get_all_users(offset, limit)


@router.put("/{user_id}/role", response_model=UserResponse)
async def change_role(
    user_id: ObjectId,
    payload: RoleUpdate,
    service: Annotated[UserService, Depends(get_user_service)],
):
    return await service.change_user_role(user_id, payload.role)
