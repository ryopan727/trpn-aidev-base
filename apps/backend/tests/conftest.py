import os
from contextlib import asynccontextmanager
from copy import deepcopy

import pytest

from app.shared.infrastructure.database import create_pool
from app.shared.infrastructure.settings import Settings


class MemoryRepository:
    def __init__(self):
        self.items = {}

    def add(self, task):
        self.items[task.id] = task

    def get(self, task_id, *, for_update=False):
        return self.items.get(task_id)

    def list(self, page, page_size):
        items = sorted(
            self.items.values(), key=lambda t: (t.created_at, t.id), reverse=True
        )
        return items[(page - 1) * page_size : page * page_size], len(items)

    def save(self, task):
        self.items[task.id] = task


class MemoryTagRepository:
    def __init__(self, tasks):
        self.tasks = tasks
        self.items = {}

    def attach(self, task_id, tag):
        key = (task_id, tag.name)
        created = key not in self.items
        self.items[key] = tag
        return created

    def detach(self, task_id, name):
        return self.items.pop((task_id, name), None) is not None

    def list(self, task_id, page, page_size):
        if self.tasks.get(task_id) is None:
            return None
        tags = sorted(
            (tag for (tid, _), tag in self.items.items() if tid == task_id),
            key=lambda tag: tag.name,
        )
        return tags[(page - 1) * page_size : page * page_size], len(tags)


class MemoryUow:
    def __init__(self):
        self.tasks = MemoryRepository()
        self.tags = MemoryTagRepository(self.tasks)
        self.committed = False
        self.fail_commit = False
        self.exited = False

    def __enter__(self):
        self.before = deepcopy(self.tasks.items)
        self.tags_before = deepcopy(self.tags.items)
        self.committed = False
        return self

    def commit(self):
        if self.fail_commit:
            raise RuntimeError("private-title db-password SQL parameter")
        self.committed = True

    def __exit__(self, *args):
        if not self.committed:
            self.tasks.items = self.before
            self.tags.items = self.tags_before
        self.exited = True


@pytest.fixture
def memory_uow():
    return MemoryUow()


@asynccontextmanager
async def no_database(app):
    yield


@pytest.fixture
def api(memory_uow):
    from fastapi.testclient import TestClient

    from app.bootstrap.tasks import get_uow
    from app.main import create_app

    app = create_app(no_database)
    app.dependency_overrides[get_uow] = lambda: memory_uow
    with TestClient(app, raise_server_exceptions=False) as client:
        yield client
    app.dependency_overrides.clear()


@pytest.fixture
def db_pool():
    settings = Settings.from_env()
    # Fail closed before any destructive query, including when dev settings leak in.
    if (
        settings.db_host != "db-test"
        or settings.db_name != os.getenv("TEST_DB_NAME")
        or not settings.db_name.endswith("_test")
    ):
        pytest.fail(
            "Database cleanup requires the explicitly configured db-test / *_test database"
        )
    pool = create_pool(settings)
    pool.open(wait=True)
    try:
        with pool.connection() as conn:
            conn.execute("TRUNCATE task_tags, tasks")
        yield pool
    finally:
        with pool.connection() as conn:
            conn.execute("TRUNCATE task_tags, tasks")
        pool.close()
