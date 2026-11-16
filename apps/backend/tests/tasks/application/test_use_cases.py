from uuid import uuid4

import pytest

from app.tasks.application.exceptions import TaskNotFound
from app.tasks.application.use_cases.complete_task import CompleteTask
from app.tasks.application.use_cases.create_task import CreateTask
from app.tasks.application.use_cases.get_task import GetTask


def test_commit_before_success_and_read_cleanup(memory_uow):
    """TASK-AC-001,008: explicit commit and scope exit before returning."""
    created = CreateTask(memory_uow).execute("task")
    assert memory_uow.committed and memory_uow.exited
    assert GetTask(memory_uow).execute(created.id) == created
    assert not memory_uow.committed and memory_uow.exited


def test_commit_failure_does_not_return_success(memory_uow):
    """TASK-AC-008."""
    memory_uow.fail_commit = True
    with pytest.raises(RuntimeError):
        CreateTask(memory_uow).execute("task")
    assert memory_uow.tasks.items == {}
    assert memory_uow.exited


def test_failed_completion_is_rolled_back(memory_uow):
    created = CreateTask(memory_uow).execute("task")
    memory_uow.fail_commit = True
    with pytest.raises(RuntimeError):
        CompleteTask(memory_uow).execute(created.id, change_status=True)
    assert memory_uow.tasks.get(created.id).status == "pending"


def test_missing_task_and_noop(memory_uow):
    """TASK-AC-006,007."""
    with pytest.raises(TaskNotFound):
        CompleteTask(memory_uow).execute(uuid4(), change_status=False)
    created = CreateTask(memory_uow).execute("task")
    assert CompleteTask(memory_uow).execute(created.id, change_status=False) == created
