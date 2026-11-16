from typing import Any
from uuid import UUID

from psycopg import Connection

from app.tasks.domain.task import Task, TaskStatus


class PostgresTaskRepository:
    def __init__(self, conn: Connection[dict[str, Any]]):
        self.conn = conn

    def add(self, task: Task) -> None:
        self.conn.execute(
            "INSERT INTO tasks (id, title, status, created_at) VALUES (%s, %s, %s, %s)",
            (task.id, task.title, task.status.value, task.created_at),
        )

    def get(self, task_id: UUID, *, for_update: bool = False) -> Task | None:
        query = "SELECT id, title, status, created_at FROM tasks WHERE id = %s"
        if for_update:
            query += " FOR UPDATE"
        row = self.conn.execute(query, (task_id,)).fetchone()
        return self._task(row) if row else None

    def list(self, page: int, page_size: int) -> tuple[list[Task], int]:
        # Both reads use the same snapshot, even when registrations occur concurrently.
        self.conn.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ")
        count = self.conn.execute("SELECT count(*) AS total FROM tasks").fetchone()
        assert count is not None
        if (page - 1) * page_size >= count["total"]:
            return [], count["total"]
        rows = self.conn.execute(
            "SELECT id, title, status, created_at FROM tasks "
            "ORDER BY created_at DESC, id DESC LIMIT %s OFFSET %s",
            (page_size, (page - 1) * page_size),
        ).fetchall()
        return [self._task(row) for row in rows], count["total"]

    def save(self, task: Task) -> None:
        self.conn.execute(
            "UPDATE tasks SET status = %s WHERE id = %s", (task.status.value, task.id)
        )

    @staticmethod
    def _task(row: dict[str, Any]) -> Task:
        return Task(
            row["id"], row["title"], TaskStatus(row["status"]), row["created_at"]
        )
