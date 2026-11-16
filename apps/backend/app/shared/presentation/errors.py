import logging
import traceback
from collections.abc import Mapping
from typing import Literal

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel
from starlette.exceptions import HTTPException
from starlette.responses import JSONResponse


class ErrorDetail(BaseModel):
    location: list[str | int]
    code: Literal["REQUIRED", "INVALID_TYPE", "INVALID_VALUE", "UNKNOWN_FIELD"]
    message: str


class ErrorBody(BaseModel):
    code: str
    message: str
    details: list[ErrorDetail]


class ErrorResponse(BaseModel):
    error: ErrorBody


def error_response(
    request: Request,
    status: int,
    code: str,
    message: str,
    details: list[ErrorDetail] | None = None,
    headers: Mapping[str, str] | None = None,
) -> JSONResponse:
    body = ErrorResponse(
        error=ErrorBody(code=code, message=message, details=details or [])
    )
    return JSONResponse(
        status_code=status,
        content=body.model_dump(),
        headers={**(headers or {}), "X-Request-ID": request.state.request_id},
    )


def validation_error(request: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, RequestValidationError)
    if any(item["type"] == "json_invalid" for item in exc.errors()):
        return error_response(
            request, 400, "INVALID_JSON", "JSONの構文を確認してください。"
        )
    details = []
    for item in exc.errors():
        kind = item["type"]
        code: Literal["REQUIRED", "INVALID_TYPE", "INVALID_VALUE", "UNKNOWN_FIELD"]
        if kind == "missing":
            code = "REQUIRED"
        elif kind == "extra_forbidden":
            code = "UNKNOWN_FIELD"
        elif kind.endswith("_type") or kind.endswith("_parsing"):
            code = "INVALID_TYPE"
        else:
            code = "INVALID_VALUE"
        details.append(
            ErrorDetail(
                location=list(item["loc"]),
                code=code,
                message="項目の指定を確認してください。",
            )
        )
    return error_response(
        request, 400, "VALIDATION_ERROR", "入力内容を確認してください。", details
    )


def http_error(request: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, HTTPException)
    return error_response(
        request,
        exc.status_code,
        "HTTP_ERROR",
        "リクエストを処理できません。",
        headers=exc.headers,
    )


def internal_error(request: Request, exc: Exception) -> JSONResponse:
    log_failure(exc, request.state.request_id)
    return error_response(
        request, 500, "INTERNAL_ERROR", "処理中にエラーが発生しました。"
    )


def log_failure(exc: Exception, request_id: str) -> None:
    frames = traceback.extract_tb(exc.__traceback__)
    locations = " > ".join(f"{f.filename}:{f.lineno}:{f.name}" for f in frames)
    logging.getLogger("app.errors").error(
        "request_id=%s exception=%s frames=%s",
        request_id,
        type(exc).__name__,
        locations,
    )
    setattr(exc, "_api_logged", True)
