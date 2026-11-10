from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.repositories.task_repo import TaskRepository
from src.repositories.user_repo import UserRepository


class UnitOfWork:
    def __init__(self, factory: async_sessionmaker[AsyncSession]):
        self.session = factory()
        self.users = UserRepository(self.session)
        self.tasks = TaskRepository(self.session)

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_value, traceback):
        # Закрытие сессии откатывает любую транзакцию, которую сервис не зафиксировал.
        await self.session.close()

    async def commit(self) -> None:
        await self.session.commit()
