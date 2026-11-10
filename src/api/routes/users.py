from fastapi import APIRouter, Depends

from src.api.dependencies import Limit, ObjectId, Offset, Uow, admin_user
from src.api.schemas.user import RoleUpdate, UserResponse
from src.services import user_service

router = APIRouter(prefix="/admin/users", tags=["admin"], dependencies=[Depends(admin_user)])


@router.get("", response_model=list[UserResponse])
async def list_users(uow: Uow, offset: Offset = 0, limit: Limit = 20):
    return await user_service.list_users(uow, offset=offset, limit=limit)


@router.put("/{user_id}/role", response_model=UserResponse)
async def change_role(user_id: ObjectId, payload: RoleUpdate, uow: Uow):
    return await user_service.change_role(uow, user_id, payload.role)
