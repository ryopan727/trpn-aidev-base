from datetime import UTC, datetime
from uuid import uuid4

from app.tasks.application.dto import TaskDTO
from app.tasks.application.ports import UnitOfWork
from app.tasks.domain.task import Task, TaskStatus


class CreateTask:
    def __init__(self, uow: UnitOfWork):
        self.uow = uow

    def execute(self, title: str) -> TaskDTO:
        task = Task(uuid4(), title, TaskStatus.PENDING, datetime.now(UTC))
        with self.uow:
            self.uow.tasks.add(task)
            self.uow.commit()
        return TaskDTO.from_task(task)
