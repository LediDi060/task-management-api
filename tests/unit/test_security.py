from datetime import UTC, datetime, timedelta

import jwt
import pytest

from src.core.config import Settings
from src.core.security import (
    ALGORITHM,
    AUDIENCE,
    ISSUER,
    create_access_token,
    hash_password,
    read_access_token,
    verify_password,
)


@pytest.mark.asyncio
async def test_bcrypt_hash_verification():
    password = "надёжныйПароль"
    hashed = await hash_password(password)
    assert hashed.startswith("$2b$")
    assert await verify_password(password, hashed)
    assert not await verify_password("another-password", hashed)


def test_token_round_trip_and_expiration():
    settings = Settings(_env_file=None)
    assert read_access_token(create_access_token(42, settings), settings) == 42
    now = datetime.now(UTC)
    expired = jwt.encode(
        {
            "sub": "42",
            "iat": now - timedelta(minutes=2),
            "exp": now - timedelta(minutes=1),
            "iss": ISSUER,
            "aud": AUDIENCE,
        },
        settings.jwt_secret.get_secret_value(),
        algorithm=ALGORITHM,
    )
    with pytest.raises(jwt.ExpiredSignatureError):
        read_access_token(expired, settings)
