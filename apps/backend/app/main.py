import logging
from collections.abc import AsyncIterator, Callable
from contextlib import AbstractAsyncContextManager, asynccontextmanager
from typing import Any

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.openapi.utils import get_openapi
from starlette.concurrency import run_in_threadpool
from starlette.exceptions import HTTPException

from app.shared.infrastructure.database import create_pool
from app.shared.infrastructure.logging import configure_logging
from app.shared.infrastructure.settings import Settings
from app.shared.presentation.access import AccessMiddleware
from app.shared.presentation.errors import http_error, internal_error, validation_error
from app.tasks.application.exceptions import TaskNotFound
from app.tasks.domain.exceptions import InvalidTaskTitle
from app.tasks.presentation.error_handlers import invalid_title, task_not_found
from app.tasks.presentation.router import router


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = Settings.from_env()
    configure_logging(settings.log_level)
    pool = create_pool(settings)
    app.state.pool = pool
    try:
        await run_in_threadpool(pool.open, wait=True)
        logging.getLogger("app.lifecycle").info("started")
        yield
    finally:
        await run_in_threadpool(pool.close)
        logging.getLogger("app.lifecycle").info("stopped")


def create_app(
    lifespan_factory: Callable[[FastAPI], AbstractAsyncContextManager] = lifespan,
) -> FastAPI:
    app = FastAPI(
        title="タスク管理API",
        version="0.1.0",
        lifespan=lifespan_factory,
        redirect_slashes=False,
    )
    app.include_router(router)
    app.add_middleware(AccessMiddleware)
    app.add_exception_handler(RequestValidationError, validation_error)
    app.add_exception_handler(HTTPException, http_error)
    app.add_exception_handler(Exception, internal_error)
    app.add_exception_handler(TaskNotFound, task_not_found)
    app.add_exception_handler(InvalidTaskTitle, invalid_title)

    def openapi() -> dict[str, Any]:
        if app.openapi_schema is None:
            schema = get_openapi(
                title=app.title, version=app.version, routes=app.routes
            )
            for path in schema["paths"].values():
                for operation in path.values():
                    if isinstance(operation, dict):
                        operation.get("responses", {}).pop("422", None)
            app.openapi_schema = schema
        return app.openapi_schema

    app.openapi = openapi  # type: ignore[method-assign]  # FastAPI schema extension hook
    return app


app = create_app()
