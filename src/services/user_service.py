from src.core.security import DUMMY_PASSWORD_HASH, hash_password, verify_password
from src.core.types import Role
from src.models.user import User
from src.services.errors import Conflict, InvalidCredentials, NotFound
from src.utils.unit_of_work import UnitOfWork


class UserService:
    def __init__(self, uow: UnitOfWork):
        self.uow = uow

    async def register_user(self, email: str, name: str, password: str) -> User:
        password_hash = await hash_password(password)
        async with self.uow as uow:
            user = await uow.users.create(
                {
                    "email": email.lower(),
                    "name": name,
                    "hashed_password": password_hash,
                    "role": Role.USER,
                }
            )
            if user is None:
                raise Conflict("Email is already registered")
            return user

    async def authenticate_user(self, email: str, password: str) -> User:
        async with self.uow as uow:
            user = await uow.users.get_by_email(email.lower())
            password_hash = user.hashed_password if user else DUMMY_PASSWORD_HASH
            matches = await verify_password(password, password_hash)
            if not user or not matches:
                raise InvalidCredentials("Invalid email or password")
            return user

    async def get_user_profile(self, user_id: int) -> User:
        async with self.uow as uow:
            user = await uow.users.get_by_id(user_id)
            if user is None:
                raise NotFound("User not found")
            return user

    async def get_all_users(self, offset: int, limit: int) -> list[User]:
        async with self.uow as uow:
            return await uow.users.get_all(offset, limit)

    async def change_user_role(self, user_id: int, role: Role) -> User:
        async with self.uow as uow:
            user = await uow.users.get_by_id(user_id)
            if user is None:
                raise NotFound("User not found")
            return await uow.users.update(user, {"role": role})
