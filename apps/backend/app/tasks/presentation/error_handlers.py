from fastapi import Request

from app.shared.presentation.errors import error_response


def task_not_found(request: Request, exc: Exception):
    return error_response(request, 404, "TASK_NOT_FOUND", "タスクが見つかりません。")


def invalid_title(request: Request, exc: Exception):
    return error_response(
        request, 400, "INVALID_TASK_TITLE", "タイトルを確認してください。"
    )
