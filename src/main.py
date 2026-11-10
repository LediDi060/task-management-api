from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from src.api.dependencies import Session
from src.api.routes import auth, tasks, users
from src.core.config import Settings
from src.core.database import create_database
from src.services.errors import (
    AccessDenied,
    Conflict,
    InvalidCredentials,
    NotFound,
    ServiceError,
)

ERROR_STATUS = {InvalidCredentials: 401, AccessDenied: 403, NotFound: 404, Conflict: 409}


async def service_error_handler(_: Request, exc: ServiceError) -> JSONResponse:
    status_code = ERROR_STATUS[type(exc)]
    headers = {"WWW-Authenticate": "Bearer"} if status_code == 401 else None
    return JSONResponse(status_code=status_code, content={"detail": str(exc)}, headers=headers)


async def validation_error_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
    # В теле запроса могут быть пароль или токен.
    errors = [
        {"loc": error["loc"], "msg": error["msg"], "type": error["type"]} for error in exc.errors()
    ]
    return JSONResponse(status_code=422, content={"detail": errors})


async def healthcheck(session: Session):
    try:
        await session.execute(text("SELECT 1"))
    except (SQLAlchemyError, OSError, TimeoutError):
        return JSONResponse(status_code=503, content={"status": "unavailable"})
    return {"status": "ok"}


def create_app(settings: Settings | None = None) -> FastAPI:
    @asynccontextmanager
    async def lifespan(application: FastAPI):
        application.state.settings = settings if settings is not None else Settings()
        engine, application.state.session_factory = create_database(
            application.state.settings.database_url
        )
        try:
            yield
        finally:
            await engine.dispose()

    application = FastAPI(title="Task Management API", version="1.0.0", lifespan=lifespan)
    application.add_exception_handler(ServiceError, service_error_handler)
    application.add_exception_handler(RequestValidationError, validation_error_handler)
    application.add_api_route("/healthz", healthcheck, methods=["GET"], tags=["health"])
    application.include_router(auth.router)
    application.include_router(tasks.router)
    application.include_router(users.router)
    return application


app = create_app()
