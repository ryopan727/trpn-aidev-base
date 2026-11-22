from urllib.parse import quote
from uuid import uuid4

import pytest

pytestmark = pytest.mark.db


def test_tag_journey(http_api, db_pool):
    """TASK-AC-011,013,014,018: actual HTTP -> Compose API -> PostgreSQL."""
    task = http_api.post("/api/v1/tasks", json={"title": "tag journey"}).json()
    other = http_api.post("/api/v1/tasks", json={"title": "other"}).json()
    url = f"/api/v1/tasks/{task['id']}/tags"
    other_url = f"/api/v1/tasks/{other['id']}/tags"
    names = ["仕事", "A", "a", "Ａ", "é", "e\u0301", "?#%"]
    assert http_api.get(url).json()["items"] == []
    for name in names:
        response = http_api.put(url + "/" + quote(name, safe=""))
        assert response.status_code == 201
        assert response.json() == {"name": name}
    tag_url = url + "/" + quote("仕事", safe="")
    assert http_api.put(tag_url).status_code == 200
    assert http_api.put(other_url + "/" + quote("仕事", safe="")).status_code == 201
    page = http_api.get(url, params={"page": 2, "page_size": 2}).json()
    assert page["items"] == [{"name": n} for n in sorted(names)[2:4]]
    assert page["total"] == len(names)
    assert http_api.get(url, params={"page": 99}).json()["items"] == []
    with db_pool.connection() as conn:
        rows = conn.execute(
            'SELECT name FROM task_tags WHERE task_id = %s ORDER BY name COLLATE "C"',
            (task["id"],),
        ).fetchall()
    assert [row["name"] for row in rows] == sorted(names)
    completed = http_api.patch(
        f"/api/v1/tasks/{task['id']}", json={"status": "completed"}
    )
    assert completed.json() == {**task, "status": "completed"}
    assert http_api.put(url + "/completed").status_code == 201
    response = http_api.delete(tag_url)
    assert response.status_code == 204 and response.content == b""
    assert http_api.delete(tag_url).json()["error"]["code"] == "TASK_TAG_NOT_FOUND"
    assert http_api.get(other_url).json()["total"] == 1
    with db_pool.connection() as conn:
        assert (
            conn.execute(
                "SELECT name FROM task_tags WHERE task_id = %s AND name = %s",
                (task["id"], "仕事"),
            ).fetchone()
            is None
        )


def test_tag_errors(http_api):
    """TASK-AC-012,015."""
    task = http_api.post("/api/v1/tasks", json={"title": "errors"}).json()
    url = f"/api/v1/tasks/{task['id']}/tags"
    for name in ["x" * 31, "a b", "a\n", "\x7f", "a\\b"]:
        assert http_api.put(url + "/" + quote(name, safe="")).status_code == 400
    for method in ("get", "put", "delete"):
        target = url if method == "get" else url + "/tag"
        response = http_api.request(method, target, content=b"{")
        assert response.status_code == 400 and "X-Request-ID" in response.headers
        missing = f"/api/v1/tasks/{uuid4()}/tags"
        response = http_api.request(
            method, missing if method == "get" else missing + "/tag"
        )
        assert response.status_code == 404
        assert response.json()["error"]["code"] == "TASK_NOT_FOUND"
    assert http_api.get(url).json()["total"] == 0


def test_database_failure_is_safe(http_api, db_pool):
    """TASK-AC-016,017: real DB failure must roll back and hide internal detail."""
    task = http_api.post("/api/v1/tasks", json={"title": "failure"}).json()
    url = f"/api/v1/tasks/{task['id']}/tags"
    with db_pool.connection() as conn:
        conn.execute("""
            CREATE FUNCTION test_tag_failure() RETURNS trigger LANGUAGE plpgsql AS $$
            BEGIN
                RAISE EXCEPTION 'E2E_PRIVATE_TAG_FAILURE';
            END;
            $$;
            CREATE TRIGGER test_tag_failure BEFORE INSERT ON task_tags
            FOR EACH ROW EXECUTE FUNCTION test_tag_failure();
        """)
    try:
        response = http_api.put(url + "/E2E_PRIVATE_TAG_NAME")
        assert response.status_code == 500
        assert response.json()["error"]["code"] == "INTERNAL_ERROR"
        assert "E2E_PRIVATE_TAG" not in response.text
        assert "X-Request-ID" in response.headers
        assert http_api.get(url).json()["total"] == 0
        with db_pool.connection() as conn:
            assert (
                conn.execute("SELECT count(*) AS n FROM task_tags").fetchone()["n"] == 0
            )
    finally:
        with db_pool.connection() as conn:
            conn.execute("DROP TRIGGER test_tag_failure ON task_tags")
            conn.execute("DROP FUNCTION test_tag_failure()")
