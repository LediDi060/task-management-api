from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.security import OAuth2PasswordRequestForm

from src.api.dependencies import (
    AppSettings,
    CurrentUser,
    get_login_form,
    get_user_service,
)
from src.api.schemas.auth import (
    LoginFormRequest,
    LoginRequest,
    RegisterRequest,
    TokenResponse,
)
from src.api.schemas.user import UserResponse
from src.core.security import create_access_token
from src.services.user_service import UserService

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserResponse)
async def register(
    payload: RegisterRequest, service: Annotated[UserService, Depends(get_user_service)]
):
    return await service.register_user(payload.email, payload.name, payload.password)


@router.post(
    "/login",
    response_model=TokenResponse,
    openapi_extra={
        "requestBody": {
            "required": True,
            "content": {
                "application/x-www-form-urlencoded": {
                    "schema": LoginFormRequest.model_json_schema()
                },
                "application/json": {"schema": LoginRequest.model_json_schema()},
            },
        }
    },
)
async def login(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends(get_login_form)],
    settings: AppSettings,
    service: Annotated[UserService, Depends(get_user_service)],
):
    user = await service.authenticate_user(form_data.username, form_data.password)
    return TokenResponse(
        access_token=create_access_token({"sub": user.email, "role": user.role}, settings)
    )


@router.get("/profile", response_model=UserResponse)
async def profile(user: CurrentUser, service: Annotated[UserService, Depends(get_user_service)]):
    return await service.get_user_profile(user.id)
