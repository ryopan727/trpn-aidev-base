from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

TaskTitle = Annotated[
    str, Field(strict=True, min_length=1, max_length=100, pattern=r"\S")
]


class TaskCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: TaskTitle


class TaskComplete(BaseModel):
    model_config = ConfigDict(extra="forbid")
    status: Literal["completed"] = Field(default_factory=lambda: "completed")


class TaskResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    title: TaskTitle
    status: Literal["pending", "completed"]
    created_at: datetime


class TaskList(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    items: list[TaskResponse]
    page: int = Field(ge=1)
    page_size: int = Field(ge=1, le=100)
    total: int = Field(ge=0)


class Pagination(BaseModel):
    model_config = ConfigDict(extra="forbid")
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)


class NoQuery(BaseModel):
    model_config = ConfigDict(extra="forbid")
