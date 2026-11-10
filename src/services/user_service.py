from src.core.security import DUMMY_PASSWORD_HASH, hash_password, verify_password
from src.core.types import Role
from src.models.user import User
from src.services.errors import Conflict, InvalidCredentials, NotFound
from src.utils.unit_of_work import UnitOfWork


async def register(uow: UnitOfWork, *, email: str, name: str, password: str) -> User:
    user = await uow.users.add(
        email=email.lower(), name=name, hashed_password=await hash_password(password)
    )
    if user is None:
        raise Conflict("Email is already registered")
    await uow.commit()
    return user


async def authenticate(uow: UnitOfWork, *, email: str, password: str) -> User:
    user = await uow.users.by_email(email.lower())
    password_hash = user.hashed_password if user else DUMMY_PASSWORD_HASH
    matches = await verify_password(password, password_hash)
    if not user or not matches:
        raise InvalidCredentials("Invalid email or password")
    return user


async def list_users(uow: UnitOfWork, *, offset: int, limit: int) -> list[User]:
    return await uow.users.list(offset, limit)


async def change_role(uow: UnitOfWork, user_id: int, role: Role) -> User:
    user = await uow.users.get(user_id)
    if user is None:
        raise NotFound("User not found")
    user.role = role
    await uow.commit()
    return user
