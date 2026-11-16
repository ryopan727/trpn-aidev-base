from uuid import UUID

from app.tasks.application.dto import TaskDTO
from app.tasks.application.exceptions import TaskNotFound
from app.tasks.application.ports import UnitOfWork


class CompleteTask:
    def __init__(self, uow: UnitOfWork):
        self.uow = uow

    def execute(self, task_id: UUID, *, change_status: bool) -> TaskDTO:
        with self.uow:
            task = self.uow.tasks.get(task_id, for_update=True)
            if task is None:
                raise TaskNotFound()
            if change_status:
                task = task.complete()
                self.uow.tasks.save(task)
            self.uow.commit()
        return TaskDTO.from_task(task)
