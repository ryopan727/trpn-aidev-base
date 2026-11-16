from uuid import UUID

import pytest

pytestmark = pytest.mark.db


def test_task_journey(http_api, db_pool):
    """TASK-AC-001,003,005,006: TCP -> Compose Uvicorn/API -> PostgreSQL."""
    created = http_api.post("/api/v1/tasks", json={"title": "タスクを試す"})
    assert created.status_code == 201
    path = created.headers["Location"]
    task = created.json()
    assert task["status"] == "pending"
    UUID(created.headers["X-Request-ID"])
    with db_pool.connection() as conn:
        row = conn.execute(
            "SELECT title, status FROM tasks WHERE id = %s", (UUID(task["id"]),)
        ).fetchone()
        assert row == {"title": task["title"], "status": "pending"}
    assert http_api.get(path).json() == task
    assert http_api.get("/api/v1/tasks").json() == {
        "items": [task],
        "page": 1,
        "page_size": 20,
        "total": 1,
    }
    assert http_api.patch(path, json={}).json() == task
    completed = http_api.patch(path, json={"status": "completed"})
    assert completed.status_code == 200
    assert completed.json() == {**task, "status": "completed"}
    with db_pool.connection() as conn:
        row = conn.execute(
            "SELECT title, status FROM tasks WHERE id = %s", (UUID(task["id"]),)
        ).fetchone()
        assert row == {"title": task["title"], "status": "completed"}
    assert http_api.patch(path, json={"status": "completed"}).json() == completed.json()
    assert http_api.get(path).json() == completed.json()
    duplicate = http_api.post("/api/v1/tasks", json={"title": "タスクを試す"})
    assert duplicate.status_code == 201
    assert duplicate.json()["id"] != task["id"]
    assert http_api.get("/api/v1/tasks?page=1&page_size=1").json()["total"] == 2


def test_rejected_inputs_do_not_change_database(http_api, db_pool):
    """TASK-AC-002,004,006,007."""
    invalid = http_api.post("/api/v1/tasks", json={"title": " "})
    assert invalid.status_code == 400
    assert invalid.json()["error"]["code"] == "VALIDATION_ERROR"
    UUID(invalid.headers["X-Request-ID"])
    malformed = http_api.post(
        "/api/v1/tasks", content="{", headers={"Content-Type": "application/json"}
    )
    assert malformed.status_code == 400
    assert malformed.json()["error"]["code"] == "INVALID_JSON"
    with db_pool.connection() as conn:
        assert conn.execute("SELECT count(*) AS total FROM tasks").fetchone() == {
            "total": 0
        }
    assert http_api.get("/api/v1/tasks").json()["total"] == 0
    created = http_api.post("/api/v1/tasks", json={"title": "task"})
    path = created.headers["Location"]
    assert http_api.patch(path, json={"status": None}).status_code == 400
    assert http_api.get(path).json() == created.json()
    with db_pool.connection() as conn:
        row = conn.execute(
            "SELECT status FROM tasks WHERE id = %s", (UUID(created.json()["id"]),)
        ).fetchone()
        assert row == {"status": "pending"}
    assert http_api.get("/api/v1/tasks?unknown=true").status_code == 400
    assert http_api.get("/api/v1/tasks?page=999").json()["items"] == []
    assert (
        http_api.get("/api/v1/tasks/00000000-0000-0000-0000-000000000000").status_code
        == 404
    )
