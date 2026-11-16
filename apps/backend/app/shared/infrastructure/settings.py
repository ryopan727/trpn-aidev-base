import os
from dataclasses import dataclass, field


@dataclass(frozen=True)
class Settings:
    db_host: str
    db_port: int
    db_name: str
    db_user: str
    db_password: str = field(repr=False)
    log_level: str = "INFO"

    @classmethod
    def from_env(cls) -> "Settings":
        def required(name: str) -> str:
            value = os.getenv(name)
            if value is None or not value.strip():
                raise ValueError(f"{name}: required")
            return value

        raw_port = required("DB_PORT")
        try:
            port = int(raw_port)
        except ValueError:
            raise ValueError("DB_PORT: must be an integer") from None
        if not 1 <= port <= 65535:
            raise ValueError("DB_PORT: out of range")
        level = os.getenv("LOG_LEVEL", "INFO")
        if level not in {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}:
            raise ValueError("LOG_LEVEL: invalid level")
        return cls(
            required("DB_HOST"),
            port,
            required("DB_NAME"),
            required("DB_USER"),
            required("DB_PASSWORD"),
            level,
        )
