import pytest

from app.operations.numbering import NumberingError, _scope_key


@pytest.mark.parametrize(
    ("scope", "expected"),
    [
        ("GLOBAL", "GLOBAL"),
        ("PROJECT", "PROJECT:7"),
        ("OPERATION_TYPE", "OPERATION_TYPE:12"),
        ("PROJECT_OPERATION_TYPE", "PROJECT:7:OPERATION_TYPE:12"),
    ],
)
def test_scope_key_supported_scopes(scope: str, expected: str) -> None:
    assert _scope_key(scope, project_id=7, operation_type_id=12) == expected


def test_scope_key_rejects_unknown_scope() -> None:
    with pytest.raises(NumberingError, match="unsupported_numbering_scope"):
        _scope_key("UNKNOWN", project_id=7, operation_type_id=12)
