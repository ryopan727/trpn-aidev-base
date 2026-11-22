from collections.abc import Iterator
from typing import Annotated

from fastapi import Depends, Request

from app.tasks.application.ports import UnitOfWork
from app.tasks.application.use_cases.complete_task import CompleteTask
from app.tasks.application.use_cases.create_task import CreateTask
from app.tasks.application.use_cases.get_task import GetTask
from app.tasks.application.use_cases.list_tasks import ListTasks
from app.tasks.application.use_cases.tags import (
    AttachTaskTag,
    DetachTaskTag,
    ListTaskTags,
)
from app.tasks.infrastructure.unit_of_work import PostgresUnitOfWork


def get_uow(request: Request) -> Iterator[UnitOfWork]:
    with request.app.state.pool.connection() as conn:
        try:
            yield PostgresUnitOfWork(conn)
        finally:
            conn.rollback()


UowDependency = Annotated[UnitOfWork, Depends(get_uow)]


def create_task(uow: UowDependency) -> CreateTask:
    return CreateTask(uow)


def get_task(uow: UowDependency) -> GetTask:
    return GetTask(uow)


def list_tasks(uow: UowDependency) -> ListTasks:
    return ListTasks(uow)


def complete_task(uow: UowDependency) -> CompleteTask:
    return CompleteTask(uow)


def attach_task_tag(uow: UowDependency) -> AttachTaskTag:
    return AttachTaskTag(uow)


def detach_task_tag(uow: UowDependency) -> DetachTaskTag:
    return DetachTaskTag(uow)


def list_task_tags(uow: UowDependency) -> ListTaskTags:
    return ListTaskTags(uow)
