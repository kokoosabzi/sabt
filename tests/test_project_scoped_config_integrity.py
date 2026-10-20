from datetime import datetime, timezone

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.models import (
    ContractNumberPolicy,
    NumberingPolicy,
    OperationType,
    OperationTypeWorkflow,
    Project,
    ProjectOperationType,
)


def test_project_scoped_policies_cannot_reference_another_projects_operation_type():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    event.listen(engine, "connect", lambda connection, _: connection.execute("PRAGMA foreign_keys=ON"))
    Base.metadata.create_all(engine)
    now = datetime.now(timezone.utc)
    try:
        with Session(engine) as session:
            project_a = Project(code="SCOPE-A", name="Scope A", status="ACTIVE",
                                 timezone="Asia/Tehran", created_at=now, updated_at=now, version=1)
            project_b = Project(code="SCOPE-B", name="Scope B", status="ACTIVE",
                                 timezone="Asia/Tehran", created_at=now, updated_at=now, version=1)
            type_b = OperationType(code="SCOPE-TYPE-B", name="Type B", active=True,
                                   system_defined=False, created_at=now, updated_at=now)
            session.add_all([project_a, project_b, type_b])
            session.flush()
            session.add(ProjectOperationType(
                project_id=project_b.id, operation_type_id=type_b.id, enabled=True,
                created_at=now, updated_at=now, version=1,
            ))
            session.commit()

            invalid_rows = [
                OperationTypeWorkflow(
                    project_id=project_a.id, operation_type_id=type_b.id, state_code="REVIEW",
                    sequence_no=1, active=True,
                ),
                NumberingPolicy(
                    project_id=project_a.id, operation_type_id=type_b.id,
                    identifier_type="OPERATION", scope="PROJECT", sequence_width=4,
                    reset_policy="NEVER", format_template="{sequence}", active=True,
                    created_at=now, updated_at=now,
                ),
                ContractNumberPolicy(
                    project_id=project_a.id, operation_type_id=type_b.id,
                    uniqueness_scope="PROJECT", active=True, created_at=now, updated_at=now,
                ),
            ]
            for row in invalid_rows:
                session.add(row)
                with pytest.raises(IntegrityError):
                    session.commit()
                session.rollback()

            # NULL project_id intentionally represents a global policy. The
            # composite FK must preserve this existing global-configuration mode.
            session.add_all([
                OperationTypeWorkflow(
                    project_id=None, operation_type_id=type_b.id, state_code="GLOBAL",
                    sequence_no=1, active=True,
                ),
                NumberingPolicy(
                    project_id=None, operation_type_id=type_b.id,
                    identifier_type="OPERATION", scope="GLOBAL", sequence_width=4,
                    reset_policy="NEVER", format_template="{sequence}", active=True,
                    created_at=now, updated_at=now,
                ),
                ContractNumberPolicy(
                    project_id=None, operation_type_id=type_b.id,
                    uniqueness_scope="GLOBAL", active=True, created_at=now, updated_at=now,
                ),
            ])
            session.commit()
    finally:
        Base.metadata.drop_all(engine)
        engine.dispose()
