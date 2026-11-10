from typing import Annotated, Literal

from pydantic import AfterValidator, BaseModel, ConfigDict, EmailStr, StringConstraints


def check_bcrypt_length(password: str) -> str:
    if len(password.encode("utf-8")) > 72:
        raise ValueError("Password must fit in 72 UTF-8 bytes")
    return password


Password = Annotated[
    str, StringConstraints(min_length=8, max_length=72), AfterValidator(check_bcrypt_length)
]
Name = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=120)]


class LoginRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: EmailStr
    password: Password


class RegisterRequest(LoginRequest):
    name: Name


class TokenResponse(BaseModel):
    access_token: str
    token_type: Literal["bearer"] = "bearer"
