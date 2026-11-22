from types import TracebackType
from typing import Protocol, Self

from app.tasks.domain.repositories import TaskRepository, TaskTagRepository


class UnitOfWork(Protocol):
    @property
    def tasks(self) -> TaskRepository: ...

    @property
    def tags(self) -> TaskTagRepository: ...

    def __enter__(self) -> Self: ...
    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None: ...
    def commit(self) -> None: ...
