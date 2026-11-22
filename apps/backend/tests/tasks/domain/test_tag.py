import pytest

from app.tasks.domain.exceptions import InvalidTaskTagName
from app.tasks.domain.tag import TaskTag


@pytest.mark.parametrize(
    "name", ["仕事", "a", "a" * 30, "A", "Ａ", "é", "e\u0301", "?#%", "😀"]
)
def test_tag_name_is_preserved(name):
    """TASK-AC-011,012: no implicit normalization."""
    assert TaskTag(name).name == name


@pytest.mark.parametrize(
    "name",
    [
        "",
        "a" * 31,
        " ",
        "a b",
        "a\n",
        "\t",
        "a/b",
        "a\\b",
        "\0",
        "\x7f",
        "\u3000",
        1,
        None,
    ],
)
def test_invalid_tag_name(name):
    with pytest.raises(InvalidTaskTagName):
        TaskTag(name)
