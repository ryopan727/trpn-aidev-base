import re
from dataclasses import dataclass

from app.tasks.domain.exceptions import InvalidTaskTagName

FORBIDDEN_TAG_CHARACTERS = r"[\s/\\\x00-\x1F\x7F]"


def valid_tag_name(name: str) -> bool:
    return (
        isinstance(name, str)
        and 1 <= len(name) <= 30
        and re.search(FORBIDDEN_TAG_CHARACTERS, name) is None
    )


@dataclass(frozen=True)
class TaskTag:
    name: str

    def __post_init__(self) -> None:
        if not valid_tag_name(self.name):
            raise InvalidTaskTagName()
