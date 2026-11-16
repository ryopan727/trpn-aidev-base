from datetime import UTC, datetime
from uuid import uuid4

import pytest

from app.tasks.domain.exceptions import InvalidTaskTitle
from app.tasks.domain.task import Task, TaskStatus


@pytest.mark.parametrize("title", ["a", "あ" * 100, " task ", "📝"])
def test_valid_title_is_preserved(title):
    """TASK-AC-001: no implicit trimming."""
    assert Task(uuid4(), title, TaskStatus.PENDING, datetime.now(UTC)).title == title


@pytest.mark.parametrize("title", ["", "a" * 101, " ", "\t\n", "\u3000", None, 1])
def test_invalid_title(title):
    """TASK-AC-002: domain rules also apply outside HTTP."""
    with pytest.raises(InvalidTaskTitle):
        Task(uuid4(), title, TaskStatus.PENDING, datetime.now(UTC))


def test_complete_is_idempotent():
    """TASK-AC-005."""
    original = Task(uuid4(), "task", TaskStatus.PENDING, datetime.now(UTC))
    completed = original.complete()
    assert completed.status == TaskStatus.COMPLETED
    assert completed.complete() == completed
    assert (completed.id, completed.title, completed.created_at) == (
        original.id,
        original.title,
        original.created_at,
    )
