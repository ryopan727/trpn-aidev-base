from uuid import UUID

from app.tasks.application.dto import TaskTagDTO, TaskTagListDTO
from app.tasks.application.exceptions import TaskNotFound, TaskTagNotFound
from app.tasks.application.ports import UnitOfWork
from app.tasks.domain.tag import TaskTag


class AttachTaskTag:
    def __init__(self, uow: UnitOfWork):
        self.uow = uow

    def execute(self, task_id: UUID, name: str) -> tuple[TaskTagDTO, bool]:
        tag = TaskTag(name)
        with self.uow:
            if self.uow.tasks.get(task_id, for_update=True) is None:
                raise TaskNotFound()
            created = self.uow.tags.attach(task_id, tag)
            self.uow.commit()
        return TaskTagDTO(tag.name), created


class DetachTaskTag:
    def __init__(self, uow: UnitOfWork):
        self.uow = uow

    def execute(self, task_id: UUID, name: str) -> None:
        tag = TaskTag(name)
        with self.uow:
            if self.uow.tasks.get(task_id, for_update=True) is None:
                raise TaskNotFound()
            if not self.uow.tags.detach(task_id, tag.name):
                raise TaskTagNotFound()
            self.uow.commit()


class ListTaskTags:
    def __init__(self, uow: UnitOfWork):
        self.uow = uow

    def execute(self, task_id: UUID, page: int, page_size: int) -> TaskTagListDTO:
        with self.uow:
            result = self.uow.tags.list(task_id, page, page_size)
            if result is None:
                raise TaskNotFound()
            tags, total = result
        return TaskTagListDTO(
            [TaskTagDTO(tag.name) for tag in tags], page, page_size, total
        )
