import asyncio
import re
import secrets
from datetime import UTC, datetime, timedelta

import bcrypt
import jwt
from jwt import InvalidTokenError

from src.core.config import Settings

ALGORITHM = "HS256"
ISSUER = "task-management-api"
AUDIENCE = "task-management-api"
DUMMY_PASSWORD_HASH = bcrypt.hashpw(secrets.token_bytes(32), bcrypt.gensalt()).decode()


async def hash_password(password: str) -> str:
    return (await asyncio.to_thread(bcrypt.hashpw, password.encode(), bcrypt.gensalt())).decode()


async def verify_password(password: str, hashed_password: str) -> bool:
    return await asyncio.to_thread(bcrypt.checkpw, password.encode(), hashed_password.encode())


def create_access_token(user_id: int, settings: Settings) -> str:
    now = datetime.now(UTC)
    return jwt.encode(
        {
            "sub": str(user_id),
            "iat": now,
            "exp": now + timedelta(minutes=settings.jwt_expire_minutes),
            "iss": ISSUER,
            "aud": AUDIENCE,
        },
        settings.jwt_secret.get_secret_value(),
        algorithm=ALGORITHM,
    )


def read_access_token(token: str, settings: Settings) -> int:
    claims = jwt.decode(
        token,
        settings.jwt_secret.get_secret_value(),
        algorithms=[ALGORITHM],
        issuer=ISSUER,
        audience=AUDIENCE,
        options={"require": ["sub", "iat", "exp", "iss", "aud"]},
    )
    subject = claims["sub"]
    if not isinstance(subject, str) or not re.fullmatch(r"[1-9][0-9]{0,9}", subject):
        raise InvalidTokenError("Invalid subject")
    user_id = int(subject)
    if user_id > 2_147_483_647:
        raise InvalidTokenError("Invalid subject")
    return user_id
