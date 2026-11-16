import logging
from uuid import UUID, uuid4

import pytest


def assert_error(response, status, code):
    assert response.status_code == status
    assert response.json()["error"]["code"] == code
    assert isinstance(response.json()["error"]["details"], list)
    UUID(response.headers["X-Request-ID"])


@pytest.mark.parametrize(
    "body",
    [
        {},
        {"title": None},
        {"title": 123},
        {"title": True},
        {"title": ""},
        {"title": " "},
        {"title": "\u3000"},
        {"title": "a" * 101},
        {"title": "task", "extra": 1},
        {"title": "task", "id": str(uuid4())},
    ],
)
def test_invalid_create(api, memory_uow, body):
    """TASK-AC-002."""
    assert_error(api.post("/api/v1/tasks", json=body), 400, "VALIDATION_ERROR")
    assert memory_uow.tasks.items == {}


def test_broken_and_missing_body(api):
    assert_error(
        api.post(
            "/api/v1/tasks", content="{", headers={"Content-Type": "application/json"}
        ),
        400,
        "INVALID_JSON",
    )
    assert_error(api.post("/api/v1/tasks"), 400, "VALIDATION_ERROR")


@pytest.mark.parametrize(
    "query",
    [
        "page=0",
        "page=-1",
        "page=abc",
        "page=1.5",
        "page_size=0",
        "page_size=101",
        "page_size=x",
        "unknown=secret",
        "sort=-created_at",
    ],
)
def test_invalid_query(api, query):
    """TASK-AC-004."""
    assert_error(api.get("/api/v1/tasks?" + query), 400, "VALIDATION_ERROR")


@pytest.mark.parametrize(
    "body",
    [
        {"status": None},
        {"status": "pending"},
        {"status": "other"},
        {"title": "task"},
        {"status": True},
    ],
)
def test_invalid_patch(api, body):
    """TASK-AC-006."""
    created = api.post("/api/v1/tasks", json={"title": "task"}).json()
    path = "/api/v1/tasks/" + created["id"]
    assert_error(api.patch(path, json=body), 400, "VALIDATION_ERROR")
    assert api.get(path).json() == created


def test_missing_noop_repeat_and_unknown_query(api):
    """TASK-AC-005,006,007."""
    path = "/api/v1/tasks/" + str(uuid4())
    for response in [
        api.get(path),
        api.patch(path, json={}),
        api.patch(path, json={"status": "completed"}),
    ]:
        assert_error(response, 404, "TASK_NOT_FOUND")
    assert_error(api.get("/api/v1/tasks/not-a-uuid"), 400, "VALIDATION_ERROR")
    assert_error(
        api.patch("/api/v1/tasks/not-a-uuid", json={}), 400, "VALIDATION_ERROR"
    )
    created_response = api.post("/api/v1/tasks", json={"title": " task "})
    assert created_response.status_code == 201
    created = created_response.json()
    assert UUID(created["id"]).version == 4
    assert created["created_at"].endswith("Z")
    path = created_response.headers["Location"]
    assert api.patch(path, json={}).json() == created
    completed = api.patch(path, json={"status": "completed"}).json()
    assert completed == {**created, "status": "completed"}
    assert api.patch(path, json={"status": "completed"}).json() == completed
    assert_error(api.patch(path), 400, "VALIDATION_ERROR")
    for response in [
        api.get(path + "?x=1"),
        api.patch(path + "?x=1", json={}),
        api.post("/api/v1/tasks?x=1", json={"title": "task"}),
    ]:
        assert_error(response, 400, "VALIDATION_ERROR")


def test_empty_list_and_default_page(api):
    assert api.get("/api/v1/tasks").json() == {
        "items": [],
        "page": 1,
        "page_size": 20,
        "total": 0,
    }
    assert api.get("/api/v1/tasks?page=999").json()["items"] == []


def test_errors_and_logs_do_not_leak_inputs(api, memory_uow, caplog):
    """TASK-AC-008,010: one sanitized failure, request-id correspondence."""
    caplog.set_level(logging.INFO)
    memory_uow.fail_commit = True
    response = api.post(
        "/api/v1/tasks",
        json={"title": "private-title"},
        headers={"X-Request-ID": "client-secret"},
    )
    assert_error(response, 500, "INTERNAL_ERROR")
    assert memory_uow.tasks.items == {}
    assert response.headers["X-Request-ID"] != "client-secret"
    for secret in ["private-title", "db-password", "SQL parameter", "client-secret"]:
        assert secret not in response.text and secret not in caplog.text
    errors = [r for r in caplog.records if r.name == "app.errors"]
    assert len(errors) == 1
    assert response.headers["X-Request-ID"] in errors[0].getMessage()
    assert "status=500" in caplog.text
    assert "RuntimeError" in caplog.text


def test_access_logs_hide_raw_path_query_and_body(api, caplog):
    caplog.set_level(logging.INFO, logger="app.access")
    api.post("/api/v1/tasks", json={"title": "private-title"})
    api.get("/api/v1/tasks/private-path?unknown=private-query")
    api.get("/unmatched-private-path")
    assert "/api/v1/tasks/{task_id}" in caplog.text
    assert "<unmatched>" in caplog.text
    for secret in ["private-title", "private-path", "private-query"]:
        assert secret not in caplog.text


def test_framework_errors_preserve_allow_header(api):
    response = api.delete("/api/v1/tasks")
    assert_error(response, 405, "HTTP_ERROR")
    assert response.headers["Allow"]


def test_generated_openapi_important_contracts(api):
    spec = api.get("/openapi.json").json()
    ids = set()
    for path in spec["paths"].values():
        for operation in path.values():
            ids.add(operation["operationId"])
            assert "422" not in operation["responses"]
            assert {"400", "500"} <= operation["responses"].keys()
            for response in operation["responses"].values():
                assert "X-Request-ID" in response["headers"]
    assert ids == {"createTask", "listTasks", "getTask", "completeTask"}
    schemas = spec["components"]["schemas"]
    assert schemas["TaskCreate"]["required"] == ["title"]
    assert schemas["TaskCreate"]["additionalProperties"] is False
    title = schemas["TaskCreate"]["properties"]["title"]
    assert (title["minLength"], title["maxLength"], title["pattern"]) == (1, 100, r"\S")
    assert not schemas["TaskComplete"].get("required")
    assert schemas["TaskComplete"]["properties"]["status"]["const"] == "completed"


def test_error_fields_are_required_in_generated_schema(api):
    schemas = api.get("/openapi.json").json()["components"]["schemas"]
    assert set(schemas["ErrorBody"]["required"]) == {"code", "message", "details"}


def test_concurrent_request_ids_are_isolated(api, caplog):
    from concurrent.futures import ThreadPoolExecutor

    caplog.set_level(logging.INFO, logger="app.access")
    with ThreadPoolExecutor(max_workers=4) as executor:
        responses = list(executor.map(lambda _: api.get("/api/v1/tasks"), range(4)))
    ids = [response.headers["X-Request-ID"] for response in responses]
    assert len(set(ids)) == 4
    messages = [
        record.getMessage() for record in caplog.records if record.name == "app.access"
    ]
    assert all(
        sum(f"request_id={value}" in msg for msg in messages) == 1 for value in ids
    )
