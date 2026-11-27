"""Seed only people/property records for the Windows transfer API smoke test."""
from __future__ import annotations

import json
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import select

from app.db.models import (
    OperationType, OperationTypeWorkflow, PartyRole, Person, Project, ProjectOperationType,
    ProjectPerson, ProjectProperty, Property,
)
from app.db.session import SessionLocal


def main() -> int:
    if len(sys.argv) != 2:
        raise SystemExit("Usage: python scripts/windows_seed_transfer.py <project-id>")
    project_id = int(sys.argv[1])
    now = datetime.now(timezone.utc)
    with SessionLocal.begin() as db:
        project = db.get(Project, project_id)
        if project is None or project.contract_code != "76":
            raise SystemExit("Windows smoke project with contract code 76 was not found.")
        operation_type = db.scalar(select(OperationType).where(
            OperationType.code == "TRANSFER", OperationType.active.is_(True), OperationType.retired_at.is_(None),
        ))
        if operation_type is None:
            raise SystemExit("Canonical TRANSFER operation type was not seeded during administrator bootstrap.")
        project_type = db.scalar(select(ProjectOperationType).where(
            ProjectOperationType.project_id == project_id,
            ProjectOperationType.operation_type_id == operation_type.id,
            ProjectOperationType.enabled.is_(True),
        ))
        if project_type is None:
            raise SystemExit("New project did not receive the default TRANSFER operation type.")
        expected_states = {"DRAFT", "IN_PROGRESS", "READY_FOR_FINALIZATION"}
        active_states = set(db.scalars(select(OperationTypeWorkflow.state_code).where(
            OperationTypeWorkflow.project_id == project_id,
            OperationTypeWorkflow.operation_type_id == operation_type.id,
            OperationTypeWorkflow.active.is_(True),
        )).all())
        if active_states != expected_states:
            raise SystemExit(f"Default transfer workflow is incomplete: {sorted(active_states)}")
        buyer_role = db.scalar(select(PartyRole).where(
            PartyRole.code == "BUYER_TRANSFEREE", PartyRole.active.is_(True), PartyRole.retired_at.is_(None),
        ))
        if buyer_role is None:
            raise SystemExit("Canonical BUYER_TRANSFEREE role was not seeded during administrator bootstrap.")

        initial_owner = Person(first_name="Windows", last_name="Initial Owner", national_id="9912345678",
                               mobile="09120000001", created_at=now, updated_at=now, version=1, is_active=True)
        buyer = Person(first_name="Windows", last_name="Approved Buyer", national_id="9912345679",
                       mobile="09120000002", created_at=now, updated_at=now, version=1, is_active=True)
        property_record = Property(unit_number="WS-101", unit_code="WINDOWS-SMOKE-101",
                                   address="Windows smoke test unit", created_at=now, updated_at=now,
                                   version=1, is_active=True)
        db.add_all([initial_owner, buyer, property_record])
        db.flush()
        db.add_all([
            ProjectPerson(project_id=project_id, person_id=initial_owner.id, active=True, created_at=now, updated_at=now),
            ProjectPerson(project_id=project_id, person_id=buyer.id, active=True, created_at=now, updated_at=now),
            ProjectProperty(project_id=project_id, property_id=property_record.id, active=True, created_at=now, updated_at=now),
        ])
        result = {
            "project_id": project_id,
            "operation_type_id": operation_type.id,
            "initial_owner_id": initial_owner.id,
            "buyer_id": buyer.id,
            "buyer_role_id": buyer_role.id,
            "property_id": property_record.id,
        }
    output = Path(tempfile.gettempdir()) / "sabt-windows-transfer-seed.json"
    output.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())