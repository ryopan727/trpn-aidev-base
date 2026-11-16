from types import TracebackType
from typing import Any, Self

from psycopg import Connection
from psycopg.pq import TransactionStatus

from app.tasks.infrastructure.repositories import PostgresTaskRepository


class PostgresUnitOfWork:
    def __init__(self, conn: Connection[dict[str, Any]]):
        self.conn = conn
        self.tasks = PostgresTaskRepository(conn)

    def __enter__(self) -> Self:
        if self.conn.info.transaction_status != TransactionStatus.IDLE:
            raise RuntimeError("Unit of Work requires an idle connection")
        # Psycopg starts the transaction before the first statement (autocommit=False).
        return self

    def commit(self) -> None:
        self.conn.commit()

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        # Finish read transactions too; never implicitly commit unconfirmed writes.
        self.conn.rollback()
