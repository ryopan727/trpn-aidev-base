from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from uuid import UUID, uuid4

import psycopg
import pytest
from psycopg.pq import TransactionStatus

from app.tasks.application.use_cases.complete_task import CompleteTask
from app.tasks.application.use_cases.create_task import CreateTask
from app.tasks.application.use_cases.list_tasks import ListTasks
from app.tasks.domain.task import Task, TaskStatus
from app.tasks.infrastructure.unit_of_work import PostgresUnitOfWork

pytestmark = pytest.mark.db


def test_real_rollback_and_connection_idle(db_pool):
    """TASK-AC-008: two writes, later failure => neither persists."""
    with db_pool.connection() as conn:
        with pytest.raises(RuntimeError):
            with PostgresUnitOfWork(conn) as uow:
                for title in ["first", "second"]:
                    uow.tasks.add(
                        Task(uuid4(), title, TaskStatus.PENDING, datetime.now(UTC))
                    )
                raise RuntimeError("force rollback")
        assert conn.info.transaction_status == TransactionStatus.IDLE
        with PostgresUnitOfWork(conn) as uow:
            assert uow.tasks.list(1, 20) == ([], 0)
        assert conn.info.transaction_status == TransactionStatus.IDLE


def test_ordering_pagination_and_parameterized_title(db_pool):
    """TASK-AC-001,003,004: tied timestamps, both states, SQL-looking input."""
    when = datetime(2026, 1, 1, tzinfo=UTC)
    with db_pool.connection() as conn:
        with PostgresUnitOfWork(conn) as uow:
            for i in range(1, 5):
                uow.tasks.add(
                    Task(
                        UUID(int=i),
                        "' ; DROP TABLE tasks; --",
                        TaskStatus.PENDING,
                        when,
                    )
                )
            uow.commit()
        CompleteTask(PostgresUnitOfWork(conn)).execute(UUID(int=4), change_status=True)
        first = ListTasks(PostgresUnitOfWork(conn)).execute(1, 2)
        second = ListTasks(PostgresUnitOfWork(conn)).execute(2, 2)
        assert [t.id.int for t in first.items + second.items] == [4, 3, 2, 1]
        assert first.total == second.total == 4
        assert first.items[0].status == "completed"
        assert first.items[0].title == "' ; DROP TABLE tasks; --"
        assert ListTasks(PostgresUnitOfWork(conn)).execute(10, 20).items == []
        assert ListTasks(PostgresUnitOfWork(conn)).execute(10**50, 100).items == []
        assert conn.info.transaction_status == TransactionStatus.IDLE


def test_completion_rollback_and_concurrent_completion(db_pool):
    """TASK-AC-005,008."""
    with db_pool.connection() as conn:
        created = CreateTask(PostgresUnitOfWork(conn)).execute("task")
        with pytest.raises(RuntimeError):
            with PostgresUnitOfWork(conn) as uow:
                uow.tasks.save(uow.tasks.get(created.id, for_update=True).complete())
                raise RuntimeError("rollback")
        with PostgresUnitOfWork(conn) as uow:
            assert uow.tasks.get(created.id).status == "pending"

    def complete(_):
        with db_pool.connection() as conn:
            return CompleteTask(PostgresUnitOfWork(conn)).execute(
                created.id, change_status=True
            )

    with ThreadPoolExecutor(max_workers=4) as executor:
        results = list(executor.map(complete, range(4)))
    assert all(result.status == "completed" for result in results)
    assert all(
        result.id == created.id and result.created_at == created.created_at
        for result in results
    )


@pytest.mark.parametrize(
    "title,status",
    [("", "pending"), ("a" * 101, "pending"), ("task", "unknown"), (None, "pending")],
)
def test_database_constraints(db_pool, title, status):
    with db_pool.connection() as conn:
        with pytest.raises(psycopg.IntegrityError):
            with PostgresUnitOfWork(conn):
                conn.execute(
                    "INSERT INTO tasks (id,title,status,created_at) VALUES (%s,%s,%s,%s)",
                    (uuid4(), title, status, datetime.now(UTC)),
                )
        assert conn.info.transaction_status == TransactionStatus.IDLE
