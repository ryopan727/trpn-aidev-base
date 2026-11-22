from typing import Any
from uuid import UUID

from psycopg import Connection

from app.tasks.domain.tag import TaskTag


class PostgresTaskTagRepository:
    def __init__(self, conn: Connection[dict[str, Any]]):
        self.conn = conn

    def attach(self, task_id: UUID, tag: TaskTag) -> bool:
        row = self.conn.execute(
            "INSERT INTO task_tags (task_id, name) VALUES (%s, %s) "
            "ON CONFLICT (task_id, name) DO NOTHING RETURNING name",
            (task_id, tag.name),
        ).fetchone()
        return row is not None

    def detach(self, task_id: UUID, name: str) -> bool:
        return (
            self.conn.execute(
                "DELETE FROM task_tags WHERE task_id = %s AND name = %s RETURNING name",
                (task_id, name),
            ).fetchone()
            is not None
        )

    def list(
        self, task_id: UUID, page: int, page_size: int
    ) -> tuple[list[TaskTag], int] | None:
        self.conn.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ")
        if (
            self.conn.execute(
                "SELECT id FROM tasks WHERE id = %s", (task_id,)
            ).fetchone()
            is None
        ):
            return None
        count = self.conn.execute(
            "SELECT count(*) AS total FROM task_tags WHERE task_id = %s", (task_id,)
        ).fetchone()
        assert count is not None
        if (page - 1) * page_size >= count["total"]:
            return [], count["total"]
        rows = self.conn.execute(
            "SELECT name FROM task_tags WHERE task_id = %s "
            'ORDER BY name COLLATE "C" LIMIT %s OFFSET %s',
            (task_id, page_size, (page - 1) * page_size),
        ).fetchall()
        return [TaskTag(row["name"]) for row in rows], count["total"]
