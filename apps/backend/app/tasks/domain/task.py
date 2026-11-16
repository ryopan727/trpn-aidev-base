from dataclasses import dataclass, replace
from datetime import datetime
from enum import StrEnum
from uuid import UUID

from app.tasks.domain.exceptions import InvalidTaskTitle


class TaskStatus(StrEnum):
    PENDING = "pending"
    COMPLETED = "completed"


@dataclass(frozen=True)
class Task:
    id: UUID
    title: str
    status: TaskStatus
    created_at: datetime

    def __post_init__(self):
        if (
            not isinstance(self.title, str)
            or not 1 <= len(self.title) <= 100
            or not self.title.strip()
        ):
            raise InvalidTaskTitle()

    def complete(self) -> "Task":
        return replace(self, status=TaskStatus.COMPLETED)
