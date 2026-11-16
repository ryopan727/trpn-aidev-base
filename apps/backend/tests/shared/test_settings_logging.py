import logging

import pytest

from app.shared.infrastructure.logging import SafeFilter, SafeFormatter
from app.shared.infrastructure.settings import Settings


def valid_env(monkeypatch):
    for key, value in {
        "DB_HOST": "db-test",
        "DB_PORT": "5432",
        "DB_NAME": "tasks_test",
        "DB_USER": "test",
        "DB_PASSWORD": "secret",
    }.items():
        monkeypatch.setenv(key, value)
    monkeypatch.delenv("LOG_LEVEL", raising=False)


@pytest.mark.parametrize(
    "name", ["DB_HOST", "DB_PORT", "DB_NAME", "DB_USER", "DB_PASSWORD"]
)
def test_missing_settings_fail_without_fallback(monkeypatch, name):
    valid_env(monkeypatch)
    monkeypatch.delenv(name)
    with pytest.raises(ValueError, match=name):
        Settings.from_env()


@pytest.mark.parametrize("port", ["", "secret", "0", "65536"])
def test_invalid_ports_do_not_echo_values(monkeypatch, port):
    valid_env(monkeypatch)
    monkeypatch.setenv("DB_PORT", port)
    with pytest.raises(ValueError) as exc:
        Settings.from_env()
    assert "secret" not in str(exc.value)


def test_settings_repr_and_log_level(monkeypatch):
    valid_env(monkeypatch)
    settings = Settings.from_env()
    assert settings.log_level == "INFO" and "secret" not in repr(settings)
    monkeypatch.setenv("LOG_LEVEL", "private-invalid")
    with pytest.raises(ValueError, match="LOG_LEVEL") as exc:
        Settings.from_env()
    assert "private-invalid" not in str(exc.value)


def test_formatter_and_filter_hide_exception_details():
    """TASK-AC-010: server/library fallback logs are also sanitized."""
    try:
        raise RuntimeError("sensitive-password")
    except RuntimeError as exc:
        record = logging.LogRecord(
            "uvicorn.error",
            logging.ERROR,
            "file",
            1,
            "sensitive-password",
            (),
            (type(exc), exc, exc.__traceback__),
        )
        assert SafeFilter().filter(record)
        output = SafeFormatter().format(record)
        assert "sensitive-password" not in output and "RuntimeError" in output
        exc._api_logged = True
        assert not SafeFilter().filter(record)
    record = logging.LogRecord(
        "psycopg.pool", logging.WARNING, "file", 1, "failed %s", ("secret",), None
    )
    assert SafeFilter().filter(record)
    assert "secret" not in record.getMessage()
