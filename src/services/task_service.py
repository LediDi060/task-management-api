from datetime import UTC, datetime

from src.core.types import Role, TaskPriority, TaskStatus
from src.models.task import Task
from src.models.user import User
from src.services.errors import NotFound
from src.utils.unit_of_work import UnitOfWork


def visible_owner(actor: User) -> int | None:
    return None if actor.role == Role.ADMIN else actor.id


async def list_tasks(
    uow: UnitOfWork,
    actor: User,
    *,
    status: TaskStatus | None,
    priority: TaskPriority | None,
    offset: int,
    limit: int,
) -> list[Task]:
    return await uow.tasks.list(
        owner_id=visible_owner(actor), status=status, priority=priority, offset=offset, limit=limit
    )


async def get_task(uow: UnitOfWork, actor: User, task_id: int, *, lock: bool = False) -> Task:
    task = await uow.tasks.get(task_id, visible_owner(actor), lock=lock)
    if task is None:
        raise NotFound("Task not found")
    return task


async def create_task(
    uow: UnitOfWork,
    actor: User,
    *,
    title: str,
    description: str | None,
    status: TaskStatus,
    priority: TaskPriority,
    deadline: datetime | None,
) -> Task:
    task = await uow.tasks.add(
        Task(
            title=title,
            description=description,
            status=status,
            priority=priority,
            deadline=deadline,
            user_id=actor.id,
        )
    )
    await uow.commit()
    return task


async def update_task(uow: UnitOfWork, actor: User, task_id: int, changes: dict) -> Task:
    task = await get_task(uow, actor, task_id, lock=True)
    for field in ("title", "description", "status", "priority", "deadline"):
        if field in changes:
            setattr(task, field, changes[field])
    if changes:
        task.updated_at = datetime.now(UTC)
    await uow.commit()
    return task


async def delete_task(uow: UnitOfWork, actor: User, task_id: int) -> None:
    task = await get_task(uow, actor, task_id, lock=True)
    await uow.tasks.delete(task)
    await uow.commit()
