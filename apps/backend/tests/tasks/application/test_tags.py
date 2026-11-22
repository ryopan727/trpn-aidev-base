from uuid import uuid4

import pytest

from app.tasks.application.exceptions import TaskNotFound, TaskTagNotFound
from app.tasks.application.use_cases.create_task import CreateTask
from app.tasks.application.use_cases.tags import (
    AttachTaskTag,
    DetachTaskTag,
    ListTaskTags,
)


def test_lifecycle_and_isolation(memory_uow):
    """TASK-AC-011,013,014,018."""
    task = CreateTask(memory_uow).execute("task")
    other = CreateTask(memory_uow).execute("other")
    attach = AttachTaskTag(memory_uow)
    assert attach.execute(task.id, "仕事")[1]
    assert not attach.execute(task.id, "仕事")[1]
    assert attach.execute(other.id, "仕事")[1]
    assert memory_uow.committed
    DetachTaskTag(memory_uow).execute(task.id, "仕事")
    assert ListTaskTags(memory_uow).execute(task.id, 1, 20).total == 0
    assert ListTaskTags(memory_uow).execute(other.id, 1, 20).total == 1
    assert not memory_uow.committed
    assert memory_uow.tasks.get(task.id).title == task.title
    with pytest.raises(TaskTagNotFound):
        DetachTaskTag(memory_uow).execute(task.id, "仕事")


@pytest.mark.parametrize("operation", ["attach", "detach", "list"])
def test_missing_parent(memory_uow, operation):
    with pytest.raises(TaskNotFound):
        if operation == "attach":
            AttachTaskTag(memory_uow).execute(uuid4(), "tag")
        elif operation == "detach":
            DetachTaskTag(memory_uow).execute(uuid4(), "tag")
        else:
            ListTaskTags(memory_uow).execute(uuid4(), 1, 20)


@pytest.mark.parametrize("remove", [False, True])
def test_tag_commit_failure_rolls_back(memory_uow, remove):
    """TASK-AC-016: never return success on commit failure."""
    task = CreateTask(memory_uow).execute("task")
    if remove:
        AttachTaskTag(memory_uow).execute(task.id, "tag")
    memory_uow.fail_commit = True
    with pytest.raises(RuntimeError):
        if remove:
            DetachTaskTag(memory_uow).execute(task.id, "tag")
        else:
            AttachTaskTag(memory_uow).execute(task.id, "tag")
    assert bool(memory_uow.tags.items) == remove
    assert memory_uow.exited
