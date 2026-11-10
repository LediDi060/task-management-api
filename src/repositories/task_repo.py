from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.types import TaskPriority, TaskStatus
from src.models.task import Task


class TaskRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def add(self, task: Task) -> Task:
        self.session.add(task)
        await self.session.flush()
        return task

    async def get(self, task_id: int, owner_id: int | None, *, lock: bool = False) -> Task | None:
        statement = select(Task).where(Task.id == task_id)
        if owner_id is not None:
            statement = statement.where(Task.user_id == owner_id)
        if lock:
            statement = statement.with_for_update()
        return await self.session.scalar(statement)

    async def list(
        self,
        *,
        owner_id: int | None,
        status: TaskStatus | None,
        priority: TaskPriority | None,
        offset: int,
        limit: int,
    ) -> list[Task]:
        statement = select(Task)
        if owner_id is not None:
            statement = statement.where(Task.user_id == owner_id)
        if status is not None:
            statement = statement.where(Task.status == status)
        if priority is not None:
            statement = statement.where(Task.priority == priority)
        result = await self.session.scalars(statement.order_by(Task.id).offset(offset).limit(limit))
        return list(result)

    async def delete(self, task: Task) -> None:
        await self.session.delete(task)
