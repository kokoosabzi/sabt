from __future__ import annotations
from datetime import datetime, timezone
import hashlib, json
from sqlalchemy import select, update
from sqlalchemy.orm import Session
from app.auth.authorization import AuthorizationContext, authorize
from app.contracts.numbering import BUYER_TRANSFEREE_ROLE_CODE, build_child_contract_number
from app.db.models import (
    Appointment, Contract, Operation, OperationAppointment, OperationParty, OperationType, OperationVersion,
    ParentContract, PartyRole, Person, PersonSnapshot, ProjectOperationType, ProjectPerson, ProjectProperty, Property, PropertySnapshot, User, WorkflowEvent,
)

class OperationError(Exception): pass
class NotFoundError(OperationError): pass
class ConflictError(OperationError): pass
class ValidationError(OperationError): pass

def _now(): return datetime.now(timezone.utc)
def _require_project_access(db, user, project_id, permission):
    authorize(db, user, permission, AuthorizationContext(project_id=project_id))
def _canonical(value): return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
def _sha(value): return hashlib.sha256(value.encode("utf-8")).hexdigest()

def _record_workflow_event(db: Session, user: User, op: Operation, event_type: str, now: datetime,
                           from_status: str | None = None, to_status: str | None = None,
                           metadata: dict | None = None) -> None:
    db.add(WorkflowEvent(project_id=op.project_id, operation_id=op.id, actor_user_id=user.id,
        event_type=event_type, from_status=from_status, to_status=to_status,
        occurred_at=now, metadata_json=_canonical(metadata) if metadata else None))

def _allocate_transfer_number(db: Session, op: Operation, now: datetime) -> None:
    """Atomically reserve the next child number inside the finalization transaction."""
    parent = db.get(ParentContract, op.parent_contract_id)
    if parent is None:
        raise NotFoundError("parent_contract_not_found")
    if parent.project_id != op.project_id or parent.status != "ACTIVE":
        raise ValidationError("parent_contract_inactive_or_project_mismatch")
    transferee_role_id = db.scalar(
        select(PartyRole.id).where(PartyRole.code == BUYER_TRANSFEREE_ROLE_CODE, PartyRole.active.is_(True),
                                   PartyRole.retired_at.is_(None))
    )
    if transferee_role_id is None:
        raise ValidationError("buyer_transferee_role_not_configured")
    transferee_count = db.scalar(
        select(OperationParty.id)
        .where(OperationParty.operation_id == op.id, OperationParty.role_id == transferee_role_id)
        .limit(1)
    )
    if transferee_count is None:
        raise ValidationError("buyer_transferee_required")

    # UPDATE ... RETURNING serializes counter changes in SQLite. The increment
    # and operation finalization share the caller's transaction; rollback undoes both.
    row = db.execute(
        update(ParentContract)
        .where(
            ParentContract.id == parent.id,
            ParentContract.project_id == op.project_id,
            ParentContract.status == "ACTIVE",
        )
        .values(
            next_transfer_sequence=ParentContract.next_transfer_sequence + 1,
            version=ParentContract.version + 1,
            updated_at=now,
        )
        .returning(ParentContract.next_transfer_sequence, ParentContract.version)
        .execution_options(synchronize_session=False)
    ).one_or_none()
    if row is None:
        raise ConflictError("parent_contract_sequence_unavailable")
    next_sequence, parent_version = row
    sequence = next_sequence - 1
    op.transfer_sequence = sequence
    op.child_contract_number = build_child_contract_number(parent.contract_number, sequence)
    parent.next_transfer_sequence = next_sequence
    parent.version = parent_version
    parent.updated_at = now

def create_operation(db: Session, user: User, project_id: int, operation_type_id: int,
                     property_id: int | None = None, appointment_id: int | None = None,
                     parent_contract_id: int | None = None) -> Operation:
    _require_project_access(db, user, project_id, "operation.create")
    ot = db.get(OperationType, operation_type_id)
    if ot is None or not ot.active or ot.retired_at is not None: raise ValidationError("operation_type_inactive")
    pot = db.scalar(select(ProjectOperationType).where(ProjectOperationType.project_id == project_id,
        ProjectOperationType.operation_type_id == operation_type_id, ProjectOperationType.enabled.is_(True)))
    if pot is None: raise ValidationError("operation_type_not_enabled_for_project")
    if property_id is not None:
        property_record = db.get(Property, property_id)
        if property_record is None: raise NotFoundError("property_not_found")
        if not property_record.is_active: raise ValidationError("property_inactive")
        association = db.get(ProjectProperty, (project_id, property_id))
        if association is None or not association.active: raise ValidationError("property_not_associated_with_project")
    if parent_contract_id is not None:
        parent = db.get(ParentContract, parent_contract_id)
        if parent is None:
            raise NotFoundError("parent_contract_not_found")
        if parent.project_id != project_id:
            raise ValidationError("parent_contract_project_mismatch")
        if parent.status != "ACTIVE":
            raise ValidationError("parent_contract_inactive")
        if parent.property_id is not None and parent.property_id != property_id:
            raise ValidationError("parent_contract_property_mismatch")
    # Validate all external references before the first write so a validation
    # failure cannot leave a partially-created Operation in the caller's unit of work.
    appointment = None
    if appointment_id is not None:
        appointment = db.get(Appointment, appointment_id)
        if appointment is None: raise NotFoundError("appointment_not_found")
        if appointment.project_id != project_id: raise ValidationError("appointment_project_mismatch")
    now = _now()
    op = Operation(project_id=project_id, operation_type_id=operation_type_id,
                   property_id=property_id, parent_contract_id=parent_contract_id,
                   status="DRAFT", current_workflow_state="DRAFT", created_by=user.id,
                   created_at=now, updated_at=now, version=1, current_version_number=0)
    db.add(op); db.flush()
    _record_workflow_event(db, user, op, "OPERATION_CREATED", now, to_status="DRAFT")
    if appointment is not None:
        db.add(OperationAppointment(appointment_id=appointment.id, operation_id=op.id, created_at=now))
        db.flush()
    return op

def add_party(db: Session, user: User, operation_id: int, person_id: int, role_id: int,
              sequence_no: int = 1, *, expected_version: int) -> OperationParty:
    op = db.get(Operation, operation_id)
    if op is None: raise NotFoundError("operation_not_found")
    _require_project_access(db, user, op.project_id, "operation.edit")
    if op.status == "FINALIZED": raise ConflictError("operation_finalized")
    if op.version != expected_version: raise ConflictError("stale_operation")
    if sequence_no < 1: raise ValidationError("party_sequence_invalid")
    person, role = db.get(Person, person_id), db.get(PartyRole, role_id)
    if person is None or not person.is_active: raise ValidationError("person_invalid")
    project_person = db.get(ProjectPerson, (op.project_id, person_id))
    if project_person is None or not project_person.active:
        raise ValidationError("person_not_associated_with_project")
    if role is None or not role.active or role.retired_at is not None: raise ValidationError("party_role_invalid")
    now = _now()
    party = OperationParty(operation_id=op.id, person_id=person_id, role_id=role_id, sequence_no=sequence_no,
                           created_at=now, updated_at=now, version=1)
    db.add(party); op.version += 1; op.updated_at = now; db.flush()
    _record_workflow_event(db, user, op, "PARTY_ADDED", now, from_status=op.status,
                           to_status=op.status, metadata={"party_id": party.id, "role_id": role_id})
    return party

def _snapshot(db: Session, op: Operation) -> dict:
    parties = []
    rows = db.scalars(select(OperationParty).where(OperationParty.operation_id == op.id)
                      .order_by(OperationParty.role_id, OperationParty.sequence_no)).all()
    for p in rows:
        person = db.get(Person, p.person_id)
        parties.append({"party_id": p.id, "person_id": p.person_id, "role_id": p.role_id, "sequence_no": p.sequence_no,
                        "person": {"first_name": person.first_name, "last_name": person.last_name,
                        "father_name": person.father_name, "national_id": person.national_id,
                        "mobile": person.mobile, "address": person.address}})
    prop = db.get(Property, op.property_id) if op.property_id else None
    return {"operation": {"id": op.id, "project_id": op.project_id, "operation_type_id": op.operation_type_id,
                           "status": op.status, "workflow_state": op.current_workflow_state,
                           "parent_contract_id": op.parent_contract_id,
                           "transfer_sequence": op.transfer_sequence,
                           "child_contract_number": op.child_contract_number},
            "property": None if prop is None else {"property_id": prop.id, "block_tower": prop.block_tower,
                "floor": prop.floor, "orientation": prop.orientation, "unit_number": prop.unit_number,
                "unit_code": prop.unit_code, "plaque_number": prop.plaque_number, "address": prop.address},
            "parties": parties}

def finalize_operation(db: Session, user: User, operation_id: int, expected_version: int,
                       reason: str | None = None) -> OperationVersion:
    op = db.get(Operation, operation_id)
    if op is None: raise NotFoundError("operation_not_found")
    _require_project_access(db, user, op.project_id, "operation.finalize")
    if op.status == "FINALIZED": raise ConflictError("operation_already_finalized")
    if op.version != expected_version: raise ConflictError("stale_operation")
    if op.property_id is None: raise ValidationError("property_required")

    now = _now()
    previous_status = op.status
    if op.parent_contract_id is not None:
        if op.transfer_sequence is not None or op.child_contract_number is not None:
            raise ConflictError("transfer_number_already_allocated")
        _allocate_transfer_number(db, op, now)
    payload = _snapshot(db, op)
    encoded = _canonical(payload)
    next_version = op.current_version_number + 1
    version = OperationVersion(operation_id=op.id, version_number=next_version, reason=reason,
                               created_by=user.id, created_at=now, finalized_at=now,
                               snapshot_json=encoded, hash=_sha(encoded))
    for party in db.scalars(select(OperationParty).where(OperationParty.operation_id == op.id)).all():
        person = db.get(Person, party.person_id)
        data = _canonical({"party_id": party.id, "person_id": party.person_id, "role_id": party.role_id,
                           "sequence_no": party.sequence_no, "person": {"first_name": person.first_name,
                           "last_name": person.last_name, "father_name": person.father_name,
                           "national_id": person.national_id, "mobile": person.mobile, "address": person.address}})
        db.add(PersonSnapshot(operation_id=op.id, person_id=party.person_id, party_id=party.id,
                              snapshot_data_json=data, created_at=now, snapshot_hash=_sha(data)))
    if op.property_id:
        prop = db.get(Property, op.property_id)
        data = _canonical({"property_id": prop.id, "block_tower": prop.block_tower, "floor": prop.floor,
                           "orientation": prop.orientation, "unit_number": prop.unit_number, "unit_code": prop.unit_code,
                           "plaque_number": prop.plaque_number, "address": prop.address})
        db.add(PropertySnapshot(operation_id=op.id, property_id=prop.id, snapshot_data_json=data,
                                created_at=now, snapshot_hash=_sha(data)))
    op.status, op.current_workflow_state = "FINALIZED", "FINALIZED"
    op.finalized_by, op.finalized_at = user.id, now
    op.current_version_number, op.version, op.updated_at = next_version, op.version + 1, now
    db.add(version); db.flush()
    _record_workflow_event(db, user, op, "OPERATION_FINALIZED", now,
                           from_status=previous_status, to_status="FINALIZED",
                           metadata={"version_number": next_version})
    return version
