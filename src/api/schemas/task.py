from datetime import UTC, datetime
from typing import Annotated

from pydantic import (
    AfterValidator,
    BaseModel,
    ConfigDict,
    StringConstraints,
    with_config,
)
from typing_extensions import TypedDict

from src.core.types import TaskPriority, TaskStatus


def normalize_deadline(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


Title = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]
Description = Annotated[str, StringConstraints(max_length=10_000)]
Deadline = Annotated[datetime, AfterValidator(normalize_deadline)]


class TaskCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: Title
    description: Description | None = None
    status: TaskStatus = TaskStatus.PENDING
    priority: TaskPriority = TaskPriority.MEDIUM
    deadline: Deadline | None = None


@with_config(ConfigDict(extra="forbid"))
class TaskUpdate(TypedDict, total=False):
    title: Title
    description: Description | None
    status: TaskStatus
    priority: TaskPriority
    deadline: Deadline | None


class TaskResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    description: str | None
    status: TaskStatus
    priority: TaskPriority
    deadline: datetime | None
    user_id: int
    created_at: datetime
    updated_at: datetime
