from fastapi import Request

from app.shared.presentation.errors import error_response


def task_not_found(request: Request, exc: Exception):
    return error_response(request, 404, "TASK_NOT_FOUND", "タスクが見つかりません。")


def invalid_title(request: Request, exc: Exception):
    return error_response(
        request, 400, "INVALID_TASK_TITLE", "タイトルを確認してください。"
    )


def tag_not_found(request: Request, exc: Exception):
    return error_response(request, 404, "TASK_TAG_NOT_FOUND", "タグが見つかりません。")


def invalid_tag_name(request: Request, exc: Exception):
    return error_response(
        request, 400, "INVALID_TASK_TAG_NAME", "タグ名を確認してください。"
    )
