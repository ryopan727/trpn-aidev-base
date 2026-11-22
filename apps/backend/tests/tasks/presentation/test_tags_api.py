import logging
from urllib.parse import quote
from uuid import uuid4

import pytest


def path(api):
    task = api.post("/api/v1/tasks", json={"title": "task"}).json()
    return f"/api/v1/tasks/{task['id']}/tags", task


def test_tags_http_contract(api):
    """TASK-AC-011,013,014,018."""
    url, task = path(api)
    name = quote("仕事?#%", safe="")
    response = api.put(f"{url}/{name}")
    assert response.status_code == 201 and response.json() == {"name": "仕事?#%"}
    assert api.put(f"{url}/{name}").status_code == 200
    assert api.get(url).json() == {
        "items": [{"name": "仕事?#%"}],
        "page": 1,
        "page_size": 20,
        "total": 1,
    }
    completed = api.patch(f"/api/v1/tasks/{task['id']}", json={"status": "completed"})
    assert set(completed.json()) == set(task)
    assert api.get(url).json()["total"] == 1
    assert api.put(f"{url}/after-completion").status_code == 201
    response = api.delete(f"{url}/{name}")
    assert response.status_code == 204 and response.content == b""
    assert "X-Request-ID" in response.headers
    response = api.delete(f"{url}/{name}")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "TASK_TAG_NOT_FOUND"


@pytest.mark.parametrize(
    "name", ["a" * 31, "a b", "a\n", "\x00", "\x7f", "a\\b", "\u3000"]
)
def test_name_validation(api, name):
    url, _ = path(api)
    for method in ("put", "delete"):
        response = getattr(api, method)(f"{url}/{quote(name, safe='')}")
        assert response.status_code == 400
        assert response.json()["error"]["code"] == "VALIDATION_ERROR"
    assert api.get(url).json()["total"] == 0


@pytest.mark.parametrize("method", ["get", "put", "delete"])
@pytest.mark.parametrize("body", [b"{}", b"{", b"null", b"secret"])
def test_body_is_rejected(api, method, body):
    url, _ = path(api)
    response = api.request(
        method, url if method == "get" else url + "/tag", content=body
    )
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"
    assert api.get(url).json()["total"] == 0


@pytest.mark.parametrize("query", ["unknown=1", "page=0", "page_size=101", "page=x"])
def test_invalid_pagination(api, query):
    url, _ = path(api)
    assert api.get(url + "?" + query).status_code == 400


def test_not_found_and_bad_identifiers(api):
    for task_id, status in [(str(uuid4()), 404), ("bad", 400)]:
        url = f"/api/v1/tasks/{task_id}/tags"
        for method in ("put", "delete", "get"):
            response = api.request(method, url if method == "get" else url + "/tag")
            assert response.status_code == status
            assert "X-Request-ID" in response.headers
    url, _ = path(api)
    for method in ("put", "delete"):
        assert api.request(method, url + "/tag?unexpected=1").status_code == 400
        assert api.request(method, url + "/").status_code == 404
        assert api.request(method, url + "/a%2Fb").status_code == 404


def test_logs_do_not_contain_names(api, memory_uow, caplog):
    """TASK-AC-017: include failed validation, unmatched routes and internal errors."""
    caplog.set_level(logging.INFO, logger="app.access")
    url, _ = path(api)
    name = "秘密Tag"
    encoded = quote(name, safe="")
    api.put(url + "/" + encoded)
    api.delete(url + "/missing-" + encoded)
    api.put(url + "/" + encoded + "%20")
    api.put(url + "/" + encoded + "/unmatched")
    memory_uow.fail_commit = True
    response = api.put(url + "/failure-" + encoded)
    assert response.status_code == 500
    assert name not in caplog.text and encoded not in caplog.text
    assert name not in response.text
    assert "{tag_name}" in caplog.text and "<unmatched>" in caplog.text


def test_tag_generated_contract(api):
    schema = api.get("/openapi.json").json()
    path = schema["paths"]["/api/v1/tasks/{task_id}/tags/{tag_name}"]
    for method in ("put", "delete"):
        operation = path[method]
        assert "requestBody" not in operation
        name = next(p for p in operation["parameters"] if p["name"] == "tag_name")
        assert name["required"]
        assert name["schema"]["minLength"] == 1
        assert name["schema"]["maxLength"] == 30
        assert "not" in name["schema"]
    assert {"200", "201", "400", "404", "500"} == set(path["put"]["responses"])
    assert "content" not in path["delete"]["responses"]["204"]
