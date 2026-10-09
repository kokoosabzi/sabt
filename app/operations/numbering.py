"""Transactional allocation for configured registration numbers.

Only NEVER reset is supported until calendar/fiscal reset semantics are frozen.
State rows are updated atomically; MAX(id)+1 is deliberately never used.
"""
from __future__ import annotations

from datetime import datetime, timezone
from sqlalchemy import select, update
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.orm import Session

from app.db.models import NumberingPolicy, NumberingState


class NumberingError(ValueError):
    pass


def _scope_key(scope: str, project_id: int, operation_type_id: int) -> str:
    if scope == "GLOBAL":
        return "GLOBAL"
    if scope == "PROJECT":
        return f"PROJECT:{project_id}"
    if scope == "OPERATION_TYPE":
        return f"OPERATION_TYPE:{operation_type_id}"
    if scope == "PROJECT_OPERATION_TYPE":
        return f"PROJECT:{project_id}:OPERATION_TYPE:{operation_type_id}"
    raise NumberingError(f"unsupported_numbering_scope:{scope}")


def _resolve_policy(db: Session, project_id: int, operation_type_id: int) -> NumberingPolicy:
    candidates = db.scalars(
        select(NumberingPolicy).where(
            NumberingPolicy.identifier_type == "REGISTRATION",
            NumberingPolicy.active.is_(True),
            ((NumberingPolicy.project_id == project_id) | (NumberingPolicy.project_id.is_(None))),
            ((NumberingPolicy.operation_type_id == operation_type_id) |
             (NumberingPolicy.operation_type_id.is_(None))),
        )
    ).all()
    if not candidates:
        raise NumberingError("registration_number_policy_missing")

    def rank(p: NumberingPolicy) -> tuple[int, int]:
        return (int(p.project_id is not None), int(p.operation_type_id is not None))

    candidates.sort(key=rank, reverse=True)
    best_rank = rank(candidates[0])
    if sum(1 for p in candidates if rank(p) == best_rank) > 1:
        raise NumberingError("ambiguous_registration_number_policy")
    return candidates[0]


def allocate_registration_number(
    db: Session, project_id: int, operation_type_id: int,
    *, now: datetime | None = None,
) -> str:
    """Allocate a number inside the caller's transaction; caller must commit/rollback."""
    policy = _resolve_policy(db, project_id, operation_type_id)
    if policy.reset_policy != "NEVER":
        raise NumberingError(f"unsupported_reset_policy:{policy.reset_policy}")
    if policy.sequence_width < 1 or policy.sequence_width > 32:
        raise NumberingError("invalid_sequence_width")

    scope_key = _scope_key(policy.scope, project_id, operation_type_id)
    timestamp = now or datetime.now(timezone.utc)
    db.execute(
        sqlite_insert(NumberingState)
        .values(numbering_policy_id=policy.id, scope_key=scope_key, current_value=0,
                updated_at=timestamp, version=1)
        .on_conflict_do_nothing(index_elements=["numbering_policy_id", "scope_key"])
    )
    next_value = db.execute(
        update(NumberingState)
        .where(NumberingState.numbering_policy_id == policy.id,
               NumberingState.scope_key == scope_key)
        .values(current_value=NumberingState.current_value + 1,
                version=NumberingState.version + 1, updated_at=timestamp)
        .returning(NumberingState.current_value)
    ).scalar_one()

    values = {
        "prefix": policy.prefix or "",
        "sequence": str(next_value).zfill(policy.sequence_width),
        "project_id": str(project_id),
        "operation_type_id": str(operation_type_id),
    }
    try:
        return policy.format_template.format(**values)
    except (KeyError, ValueError, IndexError) as exc:
        raise NumberingError("invalid_number_format_template") from exc
