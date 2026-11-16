from app.tasks.application.dto import TaskDTO, TaskPageDTO
from app.tasks.application.ports import UnitOfWork


class ListTasks:
    def __init__(self, uow: UnitOfWork):
        self.uow = uow

    def execute(self, page: int, page_size: int) -> TaskPageDTO:
        with self.uow:
            items, total = self.uow.tasks.list(page, page_size)
            return TaskPageDTO(
                [TaskDTO.from_task(item) for item in items], page, page_size, total
            )
