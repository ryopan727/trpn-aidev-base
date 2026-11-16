import pytest

pytestmark = pytest.mark.db


def test_task_journey(db_api):
    """TASK-AC-001,003,005,006: HTTP -> real PostgreSQL -> HTTP."""
    created = db_api.post("/api/v1/tasks", json={"title": "タスクを試す"})
    assert created.status_code == 201
    path = created.headers["Location"]
    task = created.json()
    assert task["status"] == "pending"
    assert db_api.get(path).json() == task
    assert db_api.get("/api/v1/tasks").json() == {
        "items": [task],
        "page": 1,
        "page_size": 20,
        "total": 1,
    }
    assert db_api.patch(path, json={}).json() == task
    completed = db_api.patch(path, json={"status": "completed"})
    assert completed.status_code == 200
    assert completed.json() == {**task, "status": "completed"}
    assert db_api.patch(path, json={"status": "completed"}).json() == completed.json()
    assert db_api.get(path).json() == completed.json()
    duplicate = db_api.post("/api/v1/tasks", json={"title": "タスクを試す"})
    assert duplicate.json()["id"] != task["id"]
    assert db_api.get("/api/v1/tasks?page=1&page_size=1").json()["total"] == 2


def test_rejected_inputs_do_not_change_database(db_api):
    """TASK-AC-002,004,006,007."""
    assert db_api.post("/api/v1/tasks", json={"title": " "}).status_code == 400
    assert db_api.get("/api/v1/tasks").json()["total"] == 0
    created = db_api.post("/api/v1/tasks", json={"title": "task"})
    path = created.headers["Location"]
    assert db_api.patch(path, json={"status": None}).status_code == 400
    assert db_api.get(path).json() == created.json()
    assert db_api.get("/api/v1/tasks?unknown=true").status_code == 400
    assert db_api.get("/api/v1/tasks?page=999").json()["items"] == []
    assert (
        db_api.get("/api/v1/tasks/00000000-0000-0000-0000-000000000000").status_code
        == 404
    )
