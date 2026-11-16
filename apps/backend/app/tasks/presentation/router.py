from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response

from app.bootstrap.tasks import complete_task, create_task, get_task, list_tasks
from app.shared.presentation.errors import ErrorResponse
from app.tasks.application.use_cases.complete_task import CompleteTask
from app.tasks.application.use_cases.create_task import CreateTask
from app.tasks.application.use_cases.get_task import GetTask
from app.tasks.application.use_cases.list_tasks import ListTasks
from app.tasks.presentation.schemas import (
    NoQuery,
    Pagination,
    TaskComplete,
    TaskCreate,
    TaskList,
    TaskResponse,
)

REQUEST_ID = {"X-Request-ID": {"schema": {"type": "string", "format": "uuid"}}}
ERRORS: dict[int | str, dict[str, Any]] = {
    400: {"model": ErrorResponse, "headers": REQUEST_ID},
    500: {"model": ErrorResponse, "headers": REQUEST_ID},
}
NOT_FOUND: dict[int | str, dict[str, Any]] = {
    404: {"model": ErrorResponse, "headers": REQUEST_ID}
}
router = APIRouter(prefix="/api/v1/tasks", tags=["tasks"], responses=ERRORS)


@router.post(
    "",
    operation_id="createTask",
    status_code=201,
    response_model=TaskResponse,
    responses={
        201: {
            "headers": {
                **REQUEST_ID,
                "Location": {"schema": {"type": "string", "format": "uri-reference"}},
            }
        }
    },
)
def register(
    body: TaskCreate,
    response: Response,
    query: Annotated[NoQuery, Query()],
    use_case: Annotated[CreateTask, Depends(create_task)],
):
    result = use_case.execute(body.title)
    response.headers["Location"] = f"/api/v1/tasks/{result.id}"
    return result


@router.get(
    "",
    operation_id="listTasks",
    response_model=TaskList,
    responses={200: {"headers": REQUEST_ID}},
)
def list_all(
    query: Annotated[Pagination, Query()],
    use_case: Annotated[ListTasks, Depends(list_tasks)],
):
    return use_case.execute(query.page, query.page_size)


@router.get(
    "/{task_id}",
    operation_id="getTask",
    response_model=TaskResponse,
    responses={200: {"headers": REQUEST_ID}, **NOT_FOUND},
)
def get_one(
    task_id: UUID,
    query: Annotated[NoQuery, Query()],
    use_case: Annotated[GetTask, Depends(get_task)],
):
    return use_case.execute(task_id)


@router.patch(
    "/{task_id}",
    operation_id="completeTask",
    response_model=TaskResponse,
    responses={200: {"headers": REQUEST_ID}, **NOT_FOUND},
)
def complete(
    task_id: UUID,
    body: TaskComplete,
    query: Annotated[NoQuery, Query()],
    use_case: Annotated[CompleteTask, Depends(complete_task)],
):
    return use_case.execute(task_id, change_status="status" in body.model_fields_set)
