import re
from typing import Annotated

from fastapi import Depends, Path, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.schemas.auth import LoginFormRequest, LoginRequest
from src.core.config import Settings
from src.core.database import get_session
from src.core.security import decode_token
from src.core.types import Role
from src.models.user import User
from src.repositories.user_repo import UserRepository
from src.services.errors import AccessDenied, InvalidCredentials
from src.services.task_service import TaskService
from src.services.user_service import UserService
from src.utils.unit_of_work import UnitOfWork

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login", auto_error=False)
Session = Annotated[AsyncSession, Depends(get_session, scope="function")]
ObjectId = Annotated[int, Path(ge=1, le=2_147_483_647)]
Offset = Annotated[int, Query(ge=0, le=2_147_483_647)]
Limit = Annotated[int, Query(ge=1, le=100)]


def get_settings(request: Request) -> Settings:
    return request.app.state.settings


AppSettings = Annotated[Settings, Depends(get_settings)]


async def get_uow(session: Session) -> UnitOfWork:
    return UnitOfWork(session)


Uow = Annotated[UnitOfWork, Depends(get_uow)]


async def get_user_service(uow: Uow) -> UserService:
    return UserService(uow)


async def get_task_service(uow: Uow) -> TaskService:
    return TaskService(uow)


async def get_user_repo(session: Session) -> UserRepository:
    return UserRepository(session)


async def get_login_form(request: Request) -> OAuth2PasswordRequestForm:
    content_type = request.headers.get("content-type", "").split(";", 1)[0].strip().lower()
    if content_type == "application/json":
        try:
            payload = await request.json()
        except ValueError:
            raise RequestValidationError(
                [{"loc": ("body",), "msg": "Invalid JSON", "type": "json_invalid"}]
            ) from None
        schema = LoginRequest
    else:
        payload = await request.form()
        schema = LoginFormRequest
    try:
        data = schema.model_validate(payload)
    except ValidationError as exc:
        errors = [{**error, "loc": ("body", *error["loc"])} for error in exc.errors()]
        raise RequestValidationError(errors) from None
    return OAuth2PasswordRequestForm(
        username=data.email, password=data.password, grant_type="password"
    )


async def get_current_user(
    token: Annotated[str | None, Depends(oauth2_scheme)],
    repo: Annotated[UserRepository, Depends(get_user_repo)],
    settings: AppSettings,
) -> User:
    if token is None:
        raise InvalidCredentials("Bearer token required")
    payload = decode_token(token, settings)
    if payload is None:
        raise InvalidCredentials("Invalid or expired bearer token")
    subject = payload["sub"]
    # Токены первой версии содержали ID пользователя в sub.
    if re.fullmatch(r"[1-9][0-9]{0,9}", subject):
        user_id = int(subject)
        if user_id > 2_147_483_647:
            raise InvalidCredentials("Invalid or expired bearer token")
        user = await repo.get_by_id(user_id)
    else:
        user = await repo.get_by_email(subject.lower())
    if user is None:
        raise InvalidCredentials("Invalid or expired bearer token")
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


class RoleChecker:
    def __init__(self, allowed_roles: list[Role]):
        self.allowed_roles = allowed_roles

    def __call__(self, current_user: CurrentUser) -> User:
        if current_user.role not in self.allowed_roles:
            raise AccessDenied("Admin role required")
        return current_user
