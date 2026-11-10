from secrets import token_urlsafe

from pydantic import EmailStr, Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_ignore_empty=True, extra="ignore", hide_input_in_errors=True
    )

    database_url: str = "postgresql+asyncpg://tasks:tasks@127.0.0.1:5432/tasks"
    jwt_secret: SecretStr = Field(default_factory=lambda: SecretStr(token_urlsafe(48)))
    jwt_expire_minutes: int = Field(default=30, ge=1, le=1440)
    smtp_host: str = "127.0.0.1"
    smtp_port: int = Field(default=1025, ge=1, le=65535)
    smtp_from: EmailStr = "tasks@example.com"

    @field_validator("jwt_secret")
    @classmethod
    def validate_jwt_secret(cls, value: SecretStr) -> SecretStr:
        if len(value.get_secret_value().encode("utf-8")) < 32:
            raise ValueError("JWT_SECRET must contain at least 32 bytes")
        return value
