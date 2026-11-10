import argparse
import asyncio

from pydantic import EmailStr, TypeAdapter, ValidationError

from src.core.config import Settings
from src.core.database import create_database
from src.core.types import Role
from src.services.user_service import UserService
from src.utils.unit_of_work import UnitOfWork


async def grant_admin(email: str) -> None:
    try:
        address = TypeAdapter(EmailStr).validate_python(email).lower()
    except ValidationError:
        raise SystemExit("Invalid email address") from None
    engine, factory = create_database(Settings().database_url)
    try:
        async with factory() as session:
            uow = UnitOfWork(session)
            user = await uow.users.get_by_email(address)
            if user is None:
                raise SystemExit("Register this user before granting the ADMIN role")
            await UserService(uow).change_user_role(user.id, Role.ADMIN)
            print(f"ADMIN role granted to {address}")
    finally:
        await engine.dispose()


def main() -> None:
    parser = argparse.ArgumentParser(description="Task Management administration")
    parser.add_argument("command", choices=["grant-admin"])
    parser.add_argument("email")
    args = parser.parse_args()
    asyncio.run(grant_admin(args.email))


if __name__ == "__main__":
    main()
