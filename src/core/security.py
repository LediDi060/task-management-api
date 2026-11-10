import asyncio
import secrets
from datetime import UTC, datetime, timedelta

from jose import JWTError, jwt
from passlib.context import CryptContext

from src.core.config import Settings

ALGORITHM = "HS256"
ISSUER = "task-management-api"
AUDIENCE = "task-management-api"
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto", bcrypt__truncate_error=True)
DUMMY_PASSWORD_HASH = pwd_context.hash(secrets.token_urlsafe(32))


async def hash_password(password: str) -> str:
    return await asyncio.to_thread(pwd_context.hash, password)


async def verify_password(password: str, hashed_password: str) -> bool:
    return await asyncio.to_thread(pwd_context.verify, password, hashed_password)


def create_access_token(
    data: dict, settings: Settings, expires_delta: timedelta | None = None
) -> str:
    now = datetime.now(UTC)
    claims = data.copy()
    claims.update(
        {
            "iat": now,
            "exp": now
            + (
                expires_delta
                if expires_delta is not None
                else timedelta(minutes=settings.jwt_expire_minutes)
            ),
            "iss": ISSUER,
            "aud": AUDIENCE,
        }
    )
    return jwt.encode(claims, settings.jwt_secret.get_secret_value(), algorithm=ALGORITHM)


def decode_token(token: str, settings: Settings) -> dict | None:
    try:
        return jwt.decode(
            token,
            settings.jwt_secret.get_secret_value(),
            algorithms=[ALGORITHM],
            issuer=ISSUER,
            audience=AUDIENCE,
            options={
                "require_sub": True,
                "require_iat": True,
                "require_exp": True,
                "require_iss": True,
                "require_aud": True,
            },
        )
    except JWTError:
        return None
