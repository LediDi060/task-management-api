from fastapi import APIRouter, status

from src.api.dependencies import AppSettings, CurrentUser, Uow
from src.api.schemas.auth import LoginRequest, RegisterRequest, TokenResponse
from src.api.schemas.user import UserResponse
from src.core.security import create_access_token
from src.services import user_service

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(payload: RegisterRequest, uow: Uow):
    return await user_service.register(
        uow, email=payload.email, name=payload.name, password=payload.password
    )


@router.post("/login", response_model=TokenResponse)
async def login(payload: LoginRequest, uow: Uow, settings: AppSettings):
    user = await user_service.authenticate(uow, email=payload.email, password=payload.password)
    return TokenResponse(access_token=create_access_token(user.id, settings))


@router.get("/profile", response_model=UserResponse)
async def profile(user: CurrentUser):
    return user
