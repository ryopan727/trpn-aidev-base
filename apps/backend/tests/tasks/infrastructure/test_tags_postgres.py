from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4

import psycopg
import pytest

from app.tasks.application.exceptions import TaskTagNotFound
from app.tasks.application.use_cases.create_task import CreateTask
from app.tasks.application.use_cases.tags import (
    AttachTaskTag,
    DetachTaskTag,
    ListTaskTags,
)
from app.tasks.domain.tag import TaskTag
from app.tasks.infrastructure.tag_repositories import PostgresTaskTagRepository
from app.tasks.infrastructure.unit_of_work import PostgresUnitOfWork

pytestmark = pytest.mark.db


def create(pool):
    with pool.connection() as conn:
        return CreateTask(PostgresUnitOfWork(conn)).execute("task")


def test_roundtrip_order_and_constraints(db_pool):
    """TASK-AC-011,012,014: exact names, stable order and database constraints."""
    task = create(db_pool)
    names = ["仕事", "a", "A", "Ａ", "é", "e\u0301"]
    with db_pool.connection() as conn:
        uow = PostgresUnitOfWork(conn)
        for name in names:
            assert AttachTaskTag(uow).execute(task.id, name)[1]
        result = ListTaskTags(uow).execute(task.id, 2, 2)
        assert [t.name for t in result.items] == sorted(names)[2:4]
        assert result.total == len(names)
        assert ListTaskTags(uow).execute(task.id, 99, 2).items == []
        assert conn.info.transaction_status == psycopg.pq.TransactionStatus.IDLE
    for params, error in [
        ((task.id, "a"), psycopg.errors.UniqueViolation),
        ((uuid4(), "new"), psycopg.errors.ForeignKeyViolation),
        ((task.id, None), psycopg.errors.NotNullViolation),
        ((task.id, "x" * 31), psycopg.errors.CheckViolation),
        ((task.id, ""), psycopg.errors.CheckViolation),
    ]:
        with pytest.raises(error), db_pool.connection() as conn:
            conn.execute("INSERT INTO task_tags VALUES (%s, %s)", params)
    with (
        pytest.raises(psycopg.errors.RestrictViolation),
        db_pool.connection() as conn,
    ):
        conn.execute("DELETE FROM tasks WHERE id = %s", (task.id,))


def test_uncommitted_changes_rollback(db_pool):
    """TASK-AC-016."""
    task = create(db_pool)
    with db_pool.connection() as conn:
        uow = PostgresUnitOfWork(conn)
        with pytest.raises(RuntimeError), uow:
            uow.tags.attach(task.id, TaskTag("tag"))
            raise RuntimeError("simulated failure")
        assert ListTaskTags(uow).execute(task.id, 1, 20).total == 0
        AttachTaskTag(uow).execute(task.id, "tag")
        with pytest.raises(RuntimeError), uow:
            uow.tags.detach(task.id, "tag")
            raise RuntimeError("simulated failure")
        assert ListTaskTags(uow).execute(task.id, 1, 20).total == 1


def test_concurrent_attach_and_detach(db_pool):
    """TASK-AC-011,016: lock serializes duplicate mutations."""
    task = create(db_pool)

    def attach():
        with db_pool.connection() as conn:
            return AttachTaskTag(PostgresUnitOfWork(conn)).execute(task.id, "tag")[1]

    def detach():
        with db_pool.connection() as conn:
            try:
                DetachTaskTag(PostgresUnitOfWork(conn)).execute(task.id, "tag")
                return True
            except TaskTagNotFound:
                return False

    with ThreadPoolExecutor(max_workers=2) as executor:
        assert sorted(executor.map(lambda _: attach(), range(2))) == [False, True]
        assert sorted(executor.map(lambda _: detach(), range(2))) == [False, True]
        futures = [executor.submit(attach), executor.submit(detach)]
        results = [f.result() for f in futures]
    with db_pool.connection() as conn:
        count = conn.execute("SELECT count(*) AS n FROM task_tags").fetchone()["n"]
    # If removal got the lock first, it returned missing and attachment remains.
    assert count == (0 if results[1] else 1)


def test_count_and_page_share_snapshot(db_pool):
    """TASK-AC-014: a concurrent write between count and items is not visible."""
    task = create(db_pool)
    with db_pool.connection() as conn:
        AttachTaskTag(PostgresUnitOfWork(conn)).execute(task.id, "b")

    class InsertAfterCount:
        def __init__(self, conn):
            self.conn = conn

        def execute(self, query, params=None):
            result = self.conn.execute(query, params)
            if "count(*)" in query:
                with db_pool.connection() as other:
                    AttachTaskTag(PostgresUnitOfWork(other)).execute(task.id, "a")
            return result

    with db_pool.connection() as conn:
        tags, count = PostgresTaskTagRepository(InsertAfterCount(conn)).list(
            task.id, 1, 20
        )
        assert count == 1 and [tag.name for tag in tags] == ["b"]
        conn.rollback()
        assert ListTaskTags(PostgresUnitOfWork(conn)).execute(task.id, 1, 20).total == 2
