from datetime import timedelta

import pytest

from src.core.config import Settings
from src.core.security import (
    create_access_token,
    decode_token,
    hash_password,
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
    data = {"sub": "student@example.com", "role": "USER"}
    token = create_access_token(data, settings)
    assert decode_token(token, settings)["sub"] == data["sub"]
    expired = create_access_token(data, settings, expires_delta=timedelta(minutes=-1))
    assert decode_token(expired, settings) is None
