from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.user import User


class UserRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, user_id: int) -> User | None:
        return await self.session.get(User, user_id)

    async def get_by_email(self, email: str) -> User | None:
        return await self.session.scalar(select(User).where(User.email == email))

    async def get_all(self, offset: int, limit: int) -> list[User]:
        result = await self.session.scalars(
            select(User).order_by(User.id).offset(offset).limit(limit)
        )
        return list(result)

    async def create(self, user_data: dict) -> User | None:
        statement = (
            insert(User)
            .values(**user_data)
            .on_conflict_do_nothing(index_elements=[User.email])
            .returning(User)
        )
        return await self.session.scalar(statement)

    async def update(self, user: User, data: dict) -> User:
        for field, value in data.items():
            setattr(user, field, value)
        await self.session.flush()
        return user
