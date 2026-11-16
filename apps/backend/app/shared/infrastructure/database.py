from typing import Any

from psycopg import Connection
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

from app.shared.infrastructure.settings import Settings


def create_pool(settings: Settings) -> ConnectionPool[Connection[dict[str, Any]]]:
    return ConnectionPool(
        kwargs={
            "host": settings.db_host,
            "port": settings.db_port,
            "dbname": settings.db_name,
            "user": settings.db_user,
            "password": settings.db_password,
            "row_factory": dict_row,
            "options": "-c timezone=UTC",
            "connect_timeout": 5,
            "autocommit": False,
        },
        min_size=1,
        max_size=5,
        timeout=10,
        open=False,
    )
