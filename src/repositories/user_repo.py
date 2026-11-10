from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.user import User


class UserRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def add(self, *, email: str, name: str, hashed_password: str) -> User | None:
        statement = (
            insert(User)
            .values(email=email, name=name, hashed_password=hashed_password)
            .on_conflict_do_nothing(index_elements=[User.email])
            .returning(User)
        )
        return await self.session.scalar(statement)

    async def get(self, user_id: int) -> User | None:
        return await self.session.get(User, user_id)

    async def by_email(self, email: str) -> User | None:
        return await self.session.scalar(select(User).where(User.email == email))

    async def list(self, offset: int, limit: int) -> list[User]:
        result = await self.session.scalars(
            select(User).order_by(User.id).offset(offset).limit(limit)
        )
        return list(result)
