from __future__ import annotations

from datetime import datetime, timezone
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import OperationType, OperationTypeWorkflow, PartyRole, ProjectOperationType

TRANSFER_OPERATION_TYPE_CODE = "TRANSFER"
BUYER_TRANSFEREE_ROLE_CODE = "BUYER_TRANSFEREE"
DEFAULT_TRANSFER_STATES = (
    ("DRAFT", 1),
    ("IN_PROGRESS", 2),
    ("READY_FOR_FINALIZATION", 3),
)


class OperationCatalogError(RuntimeError):
    pass


def ensure_system_operation_catalog(db: Session) -> tuple[OperationType, PartyRole]:
    now = datetime.now(timezone.utc)
    operation_type = db.scalar(select(OperationType).where(OperationType.code == TRANSFER_OPERATION_TYPE_CODE))
    if operation_type is None:
        operation_type = OperationType(
            code=TRANSFER_OPERATION_TYPE_CODE, name="انتقال مالکیت",
            description="انتقال مالکیت در زنجیره قرارداد مادر.", active=True,
            system_defined=True, retired_at=None, created_at=now, updated_at=now,
        )
        db.add(operation_type)
        db.flush()
    elif not operation_type.active or operation_type.retired_at is not None:
        raise OperationCatalogError("default_transfer_operation_type_inactive")

    buyer_role = db.scalar(select(PartyRole).where(PartyRole.code == BUYER_TRANSFEREE_ROLE_CODE))
    if buyer_role is None:
        buyer_role = PartyRole(
            code=BUYER_TRANSFEREE_ROLE_CODE, name="خریدار / منتقل‌الیه مورد تأیید",
            description="طرفی که پس از نهایی‌شدن انتقال، مالک فعلی قرارداد مادر محسوب می‌شود.",
            active=True, system_defined=True, retired_at=None, created_at=now, updated_at=now,
        )
        db.add(buyer_role)
        db.flush()
    elif not buyer_role.active or buyer_role.retired_at is not None:
        raise OperationCatalogError("buyer_transferee_role_inactive")
    return operation_type, buyer_role


def ensure_project_transfer_workflow(db: Session, project_id: int) -> OperationType:
    operation_type, _ = ensure_system_operation_catalog(db)
    project_type = db.scalar(select(ProjectOperationType).where(
        ProjectOperationType.project_id == project_id,
        ProjectOperationType.operation_type_id == operation_type.id,
    ))
    if project_type is None:
        now = datetime.now(timezone.utc)
        project_type = ProjectOperationType(
            project_id=project_id, operation_type_id=operation_type.id, enabled=True,
            created_at=now, updated_at=now, version=1,
        )
        db.add(project_type)
        db.flush()
    if not project_type.enabled:
        raise OperationCatalogError("project_transfer_operation_disabled")

    for state_code, sequence_no in DEFAULT_TRANSFER_STATES:
        state = db.scalar(select(OperationTypeWorkflow).where(
            OperationTypeWorkflow.project_id == project_id,
            OperationTypeWorkflow.operation_type_id == operation_type.id,
            OperationTypeWorkflow.state_code == state_code,
        ))
        if state is None:
            db.add(OperationTypeWorkflow(
                project_id=project_id, operation_type_id=operation_type.id,
                state_code=state_code, sequence_no=sequence_no, active=True,
            ))
        elif not state.active:
            raise OperationCatalogError(f"project_transfer_state_inactive:{state_code}")
    db.flush()
    return operation_type