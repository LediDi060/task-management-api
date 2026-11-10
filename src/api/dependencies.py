from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import Depends, Path, Query, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import InvalidTokenError

from src.core.config import Settings
from src.core.security import read_access_token
from src.core.types import Role
from src.models.user import User
from src.services.errors import AccessDenied, InvalidCredentials
from src.utils.unit_of_work import UnitOfWork

bearer = HTTPBearer(auto_error=False)


def get_settings(request: Request) -> Settings:
    return request.app.state.settings


async def get_uow(request: Request) -> AsyncIterator[UnitOfWork]:
    async with UnitOfWork(request.app.state.session_factory) as uow:
        yield uow


AppSettings = Annotated[Settings, Depends(get_settings)]
Uow = Annotated[UnitOfWork, Depends(get_uow, scope="function")]
ObjectId = Annotated[int, Path(ge=1, le=2_147_483_647)]
Offset = Annotated[int, Query(ge=0, le=2_147_483_647)]
Limit = Annotated[int, Query(ge=1, le=100)]


async def current_user(
    uow: Uow,
    settings: AppSettings,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
) -> User:
    if credentials is None:
        raise InvalidCredentials("Bearer token required")
    try:
        user_id = read_access_token(credentials.credentials, settings)
    except InvalidTokenError:
        raise InvalidCredentials("Invalid or expired bearer token") from None
    user = await uow.users.get(user_id)
    if user is None:
        raise InvalidCredentials("Invalid or expired bearer token")
    return user


CurrentUser = Annotated[User, Depends(current_user)]


async def admin_user(user: CurrentUser) -> User:
    if user.role != Role.ADMIN:
        raise AccessDenied("Admin role required")
    return user
