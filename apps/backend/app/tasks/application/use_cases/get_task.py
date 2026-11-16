from uuid import UUID

from app.tasks.application.dto import TaskDTO
from app.tasks.application.exceptions import TaskNotFound
from app.tasks.application.ports import UnitOfWork


class GetTask:
    def __init__(self, uow: UnitOfWork):
        self.uow = uow

    def execute(self, task_id: UUID) -> TaskDTO:
        with self.uow:
            task = self.uow.tasks.get(task_id)
            if task is None:
                raise TaskNotFound()
            return TaskDTO.from_task(task)
