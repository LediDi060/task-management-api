from datetime import UTC, datetime

from src.core.types import Role, TaskPriority, TaskStatus
from src.models.task import Task
from src.models.user import User
from src.services.errors import NotFound
from src.utils.unit_of_work import UnitOfWork


class TaskService:
    def __init__(self, uow: UnitOfWork):
        self.uow = uow

    @staticmethod
    def _owner_id(actor: User) -> int | None:
        return None if actor.role == Role.ADMIN else actor.id

    async def _get_task(self, actor: User, task_id: int, *, lock: bool = False) -> Task:
        task = await self.uow.tasks.get_by_id(task_id, self._owner_id(actor), lock=lock)
        if task is None:
            raise NotFound("Task not found")
        return task

    async def get_all_tasks(
        self,
        actor: User,
        *,
        status: TaskStatus | None,
        priority: TaskPriority | None,
        offset: int,
        limit: int,
    ) -> list[Task]:
        async with self.uow as uow:
            return await uow.tasks.get_all(
                owner_id=self._owner_id(actor),
                status=status,
                priority=priority,
                offset=offset,
                limit=limit,
            )

    async def get_task_by_id(self, actor: User, task_id: int) -> Task:
        async with self.uow:
            return await self._get_task(actor, task_id)

    async def create_task(
        self,
        actor: User,
        *,
        title: str,
        description: str | None,
        status: TaskStatus,
        priority: TaskPriority,
        deadline: datetime | None,
    ) -> Task:
        async with self.uow as uow:
            return await uow.tasks.create(
                {
                    "title": title,
                    "description": description,
                    "status": status,
                    "priority": priority,
                    "deadline": deadline,
                    "user_id": actor.id,
                }
            )

    async def update_task(self, actor: User, task_id: int, changes: dict) -> Task:
        async with self.uow as uow:
            task = await self._get_task(actor, task_id, lock=True)
            data = {
                field: changes[field]
                for field in ("title", "description", "status", "priority", "deadline")
                if field in changes
            }
            if data:
                data["updated_at"] = datetime.now(UTC)
            return await uow.tasks.update(task, data)

    async def delete_task(self, actor: User, task_id: int) -> None:
        async with self.uow as uow:
            task = await self._get_task(actor, task_id, lock=True)
            await uow.tasks.delete(task)
