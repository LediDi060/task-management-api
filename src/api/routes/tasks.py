from fastapi import APIRouter, BackgroundTasks, status

from src.api.dependencies import AppSettings, CurrentUser, Limit, ObjectId, Offset, Uow
from src.api.schemas.task import TaskCreate, TaskResponse, TaskUpdate
from src.core.types import TaskPriority, TaskStatus
from src.services import notifications, task_service

router = APIRouter(prefix="/tasks", tags=["tasks"])


@router.get("", response_model=list[TaskResponse])
async def list_tasks(
    uow: Uow,
    user: CurrentUser,
    status: TaskStatus | None = None,
    priority: TaskPriority | None = None,
    offset: Offset = 0,
    limit: Limit = 20,
):
    return await task_service.list_tasks(
        uow, user, status=status, priority=priority, offset=offset, limit=limit
    )


@router.get("/{task_id}", response_model=TaskResponse)
async def get_task(task_id: ObjectId, uow: Uow, user: CurrentUser):
    return await task_service.get_task(uow, user, task_id)


@router.post("", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
async def create_task(
    payload: TaskCreate,
    background_tasks: BackgroundTasks,
    uow: Uow,
    user: CurrentUser,
    settings: AppSettings,
):
    task = await task_service.create_task(uow, user, **payload.model_dump())
    background_tasks.add_task(
        notifications.send_task_created, settings, user.email, task.id, task.title
    )
    return task


@router.put("/{task_id}", response_model=TaskResponse)
async def update_task(task_id: ObjectId, payload: TaskUpdate, uow: Uow, user: CurrentUser):
    return await task_service.update_task(uow, user, task_id, payload)


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
async def delete_task(task_id: ObjectId, uow: Uow, user: CurrentUser) -> None:
    await task_service.delete_task(uow, user, task_id)
