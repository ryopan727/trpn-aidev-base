from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, Response
from fastapi.exceptions import RequestValidationError
from pydantic import AfterValidator, BaseModel, ConfigDict, Field, WithJsonSchema

from app.bootstrap.tasks import attach_task_tag, detach_task_tag, list_task_tags
from app.tasks.application.use_cases.tags import (
    AttachTaskTag,
    DetachTaskTag,
    ListTaskTags,
)
from app.tasks.domain.tag import FORBIDDEN_TAG_CHARACTERS, valid_tag_name
from app.tasks.presentation.router import ERRORS, NOT_FOUND, REQUEST_ID
from app.tasks.presentation.schemas import NoQuery, Pagination


def validate_name(value: str) -> str:
    if not valid_tag_name(value):
        raise ValueError("タグ名を確認してください。")
    return value


TagName = Annotated[
    str,
    Field(strict=True, min_length=1, max_length=30),
    AfterValidator(validate_name),
    WithJsonSchema(
        {
            "type": "string",
            "minLength": 1,
            "maxLength": 30,
            "not": {"pattern": FORBIDDEN_TAG_CHARACTERS},
        }
    ),
]


class TagResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")
    name: TagName


class TagList(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    items: list[TagResponse]
    page: int = Field(ge=1)
    page_size: int = Field(ge=1, le=100)
    total: int = Field(ge=0)


async def reject_body(request: Request) -> None:
    # Read transport bytes only; application/database work remains synchronous.
    if await request.body():
        raise RequestValidationError(
            [
                {
                    "type": "extra_forbidden",
                    "loc": ("body",),
                    "msg": "本文は指定できません。",
                }
            ]
        )


router = APIRouter(
    prefix="/api/v1/tasks/{task_id}/tags",
    tags=["tasks"],
    dependencies=[Depends(reject_body)],
    responses={**ERRORS, **NOT_FOUND},
)


@router.put(
    "/{tag_name}",
    operation_id="attachTaskTag",
    response_model=TagResponse,
    responses={
        200: {"headers": REQUEST_ID},
        201: {"model": TagResponse, "headers": REQUEST_ID},
    },
)
def attach(
    task_id: UUID,
    tag_name: TagName,
    query: Annotated[NoQuery, Query()],
    response: Response,
    use_case: Annotated[AttachTaskTag, Depends(attach_task_tag)],
):
    tag, created = use_case.execute(task_id, tag_name)
    response.status_code = 201 if created else 200
    return tag


@router.delete(
    "/{tag_name}",
    operation_id="detachTaskTag",
    status_code=204,
    responses={204: {"headers": REQUEST_ID}},
)
def detach(
    task_id: UUID,
    tag_name: TagName,
    query: Annotated[NoQuery, Query()],
    use_case: Annotated[DetachTaskTag, Depends(detach_task_tag)],
) -> Response:
    use_case.execute(task_id, tag_name)
    return Response(status_code=204)


@router.get(
    "",
    operation_id="listTaskTags",
    response_model=TagList,
    responses={200: {"headers": REQUEST_ID}},
)
def list_all(
    task_id: UUID,
    query: Annotated[Pagination, Query()],
    use_case: Annotated[ListTaskTags, Depends(list_task_tags)],
):
    return use_case.execute(task_id, query.page, query.page_size)
