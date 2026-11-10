from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, status

from src.api.dependencies import (
    AppSettings,
    CurrentUser,
    Limit,
    ObjectId,
    Offset,
    get_task_service,
)
from src.api.schemas.task import TaskCreate, TaskResponse, TaskUpdate
from src.core.types import TaskPriority, TaskStatus
from src.services import notifications
from src.services.task_service import TaskService

router = APIRouter(prefix="/tasks", tags=["tasks"])


@router.get("", response_model=list[TaskResponse])
async def list_tasks(
    user: CurrentUser,
    service: Annotated[TaskService, Depends(get_task_service)],
    status: TaskStatus | None = None,
    priority: TaskPriority | None = None,
    offset: Offset = 0,
    limit: Limit = 20,
):
    return await service.get_all_tasks(
        user, status=status, priority=priority, offset=offset, limit=limit
    )


@router.get("/{task_id}", response_model=TaskResponse)
async def get_task(
    task_id: ObjectId, user: CurrentUser, service: Annotated[TaskService, Depends(get_task_service)]
):
    return await service.get_task_by_id(user, task_id)


@router.post("", response_model=TaskResponse)
async def create_task(
    payload: TaskCreate,
    background_tasks: BackgroundTasks,
    user: CurrentUser,
    settings: AppSettings,
    service: Annotated[TaskService, Depends(get_task_service)],
):
    task = await service.create_task(user, **payload.model_dump())
    background_tasks.add_task(
        notifications.send_task_created, settings, user.email, task.id, task.title
    )
    return task


@router.put("/{task_id}", response_model=TaskResponse)
async def update_task(
    task_id: ObjectId,
    payload: TaskUpdate,
    user: CurrentUser,
    service: Annotated[TaskService, Depends(get_task_service)],
):
    return await service.update_task(user, task_id, payload)


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
async def delete_task(
    task_id: ObjectId, user: CurrentUser, service: Annotated[TaskService, Depends(get_task_service)]
) -> None:
    await service.delete_task(user, task_id)
