import logging
import sys
import time
import traceback


class SafeFormatter(logging.Formatter):
    def converter(self, timestamp: float | None = None):
        return time.gmtime(timestamp) if timestamp is not None else time.gmtime()

    def formatException(self, ei):
        # Omit messages, chained exceptions, locals and source text.
        frames = traceback.extract_tb(ei[2])
        locations = " > ".join(f"{f.filename}:{f.lineno}:{f.name}" for f in frames)
        return f"exception={ei[0].__name__} frames={locations}"


class SafeFilter(logging.Filter):
    def filter(self, record):
        if record.exc_info and getattr(record.exc_info[1], "_api_logged", False):
            return False
        # Connection-pool diagnostics may interpolate credentials or server messages.
        if record.name.startswith("psycopg"):
            record.msg = "database pool event (details omitted)"
            record.args = ()
        if record.exc_info:
            record.msg = "unhandled failure"
            record.args = ()
        return True


def configure_logging(level: str) -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        SafeFormatter(
            "%(asctime)sZ %(levelname)s logger=%(name)s %(message)s",
            datefmt="%Y-%m-%dT%H:%M:%S",
        )
    )
    handler.addFilter(SafeFilter())
    logging.basicConfig(level=level, handlers=[handler], force=True)
    for name in ("uvicorn", "uvicorn.error", "psycopg", "psycopg.pool"):
        logger = logging.getLogger(name)
        logger.handlers.clear()
        logger.propagate = True
    # HTTPX test-client diagnostics include raw request URLs.
    logging.getLogger("httpx").setLevel(logging.WARNING)
