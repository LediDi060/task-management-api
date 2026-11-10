from email.message import EmailMessage
from pathlib import Path

import pytest
import pytest_asyncio
from alembic.config import Config
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from testcontainers.postgres import PostgresContainer

from alembic import command
from src.core.config import Settings
from src.main import create_app
from src.services import notifications

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="session")
def database_url():
    with PostgresContainer("postgres:16-alpine", driver="asyncpg") as postgres:
        url = postgres.get_connection_url()
        config = Config(str(ROOT / "alembic.ini"))
        config.attributes["database_url"] = url
        command.upgrade(config, "head")
        command.check(config)
        yield url


@pytest.fixture
def smtp_messages(monkeypatch) -> list[EmailMessage]:
    messages: list[EmailMessage] = []

    class RecordingSMTP:
        def __init__(self, host, port, timeout):
            assert (host, port, timeout) == ("smtp.test", 1025, 5)

        def __enter__(self):
            return self

        def __exit__(self, *exc):
            pass

        def send_message(self, message):
            messages.append(message)

    monkeypatch.setattr(notifications.smtplib, "SMTP", RecordingSMTP)
    return messages


@pytest_asyncio.fixture
async def app(database_url, smtp_messages):
    settings = Settings(
        _env_file=None,
        database_url=database_url,
        smtp_host="smtp.test",
        smtp_port=1025,
        smtp_from="tasks@example.com",
        jwt_expire_minutes=30,
    )
    application = create_app(settings)
    async with application.router.lifespan_context(application):
        async with application.state.session_factory.begin() as session:
            await session.execute(text("TRUNCATE TABLE tasks, users RESTART IDENTITY"))
        yield application


@pytest_asyncio.fixture
async def async_client(app):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield client


@pytest.fixture
def account(async_client, app):
    async def create(email: str, *, admin: bool = False):
        payload = {"email": email, "password": "secure123"}
        response = await async_client.post("/auth/register", json={**payload, "name": "Test User"})
        assert response.status_code == 201, response.text
        user = response.json()
        if admin:
            async with app.state.session_factory.begin() as session:
                await session.execute(
                    text("UPDATE users SET role = 'ADMIN' WHERE id = :user_id"),
                    {"user_id": user["id"]},
                )
        response = await async_client.post("/auth/login", json=payload)
        assert response.status_code == 200, response.text
        return user, {"Authorization": f"Bearer {response.json()['access_token']}"}

    return create
