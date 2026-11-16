from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from app.tasks.domain.task import Task, TaskStatus


@dataclass(frozen=True)
class TaskDTO:
    id: UUID
    title: str
    status: TaskStatus
    created_at: datetime

    @classmethod
    def from_task(cls, task: Task) -> "TaskDTO":
        return cls(task.id, task.title, task.status, task.created_at)


@dataclass(frozen=True)
class TaskPageDTO:
    items: list[TaskDTO]
    page: int
    page_size: int
    total: int
