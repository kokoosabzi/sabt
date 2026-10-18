from datetime import datetime, timezone

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.models import NumberingPolicy, NumberingState, OperationType
from app.operations.numbering import NumberingError, _scope_key, allocate_registration_number


@pytest.fixture()
def db():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session
    Base.metadata.drop_all(engine)
    engine.dispose()


def add_policy(db: Session, **overrides) -> NumberingPolicy:
    now = datetime.now(timezone.utc)
    values = {
        "identifier_type": "REGISTRATION",
        "scope": "GLOBAL",
        "prefix": "REG-",
        "sequence_width": 3,
        "reset_policy": "NEVER",
        "format_template": "{prefix}{sequence}",
        "active": True,
        "created_at": now,
        "updated_at": now,
    }
    values.update(overrides)
    policy = NumberingPolicy(**values)
    db.add(policy)
    db.flush()
    return policy


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


def test_registration_numbers_increment_atomically_within_transaction(db: Session) -> None:
    add_policy(db)
    assert allocate_registration_number(db, 7, 12) == "REG-001"
    assert allocate_registration_number(db, 7, 12) == "REG-002"
    db.commit()

    state = db.scalar(select(NumberingState))
    assert state is not None
    assert state.current_value == 2


def test_registration_number_allocation_rolls_back_with_caller_transaction(db: Session) -> None:
    add_policy(db)
    first = allocate_registration_number(db, 7, 12)
    assert first == "REG-001"
    db.rollback()

    # The policy was part of the same transaction and rolled back as well;
    # create it again to verify that a failed caller transaction consumes no number.
    add_policy(db)
    assert allocate_registration_number(db, 7, 12) == "REG-001"


def test_ambiguous_equally_specific_registration_policies_are_rejected(db: Session) -> None:
    add_policy(db, project_id=7, operation_type_id=12)
    add_policy(db, project_id=7, operation_type_id=12)

    with pytest.raises(NumberingError, match="ambiguous_registration_number_policy"):
        allocate_registration_number(db, 7, 12)


def test_unsupported_reset_policy_is_rejected(db: Session) -> None:
    add_policy(db, reset_policy="YEARLY")

    with pytest.raises(NumberingError, match="unsupported_reset_policy"):
        allocate_registration_number(db, 7, 12)


def test_invalid_format_template_is_rejected_without_consuming_number(db: Session) -> None:
    add_policy(db, format_template="{unknown}")
    with pytest.raises(NumberingError, match="invalid_number_format_template"):
        allocate_registration_number(db, 7, 12)

    # The caller may catch the validation error and continue its transaction;
    # invalid configuration must not have created or incremented sequence state.
    assert db.scalar(select(NumberingState)) is None


def test_format_template_attribute_access_is_rejected_before_allocation(db: Session) -> None:
    add_policy(db, format_template="{prefix.upper}")
    with pytest.raises(NumberingError, match="invalid_number_format_template"):
        allocate_registration_number(db, 7, 12)

    assert db.scalar(select(NumberingState)) is None
