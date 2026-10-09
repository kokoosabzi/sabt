from __future__ import annotations
from datetime import datetime, timezone
import hashlib, json
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.auth.authorization import AuthorizationContext, authorize
from app.db.models import (
    Appointment, Contract, Operation, OperationAppointment, OperationParty, OperationType, OperationVersion,
    PartyRole, Person, PersonSnapshot, ProjectOperationType, ProjectProperty, Property, PropertySnapshot, User,
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

def create_operation(db: Session, user: User, project_id: int, operation_type_id: int,
                     property_id: int | None = None, appointment_id: int | None = None) -> Operation:
    _require_project_access(db, user, project_id, "operation.create")
    ot = db.get(OperationType, operation_type_id)
    if ot is None or not ot.active or ot.retired_at is not None: raise ValidationError("operation_type_inactive")
    pot = db.scalar(select(ProjectOperationType).where(ProjectOperationType.project_id == project_id,
        ProjectOperationType.operation_type_id == operation_type_id, ProjectOperationType.enabled.is_(True)))
    if pot is None: raise ValidationError("operation_type_not_enabled_for_project")
    if property_id is not None:
        if db.get(Property, property_id) is None: raise NotFoundError("property_not_found")
        association = db.get(ProjectProperty, (project_id, property_id))
        if association is None or not association.active: raise ValidationError("property_not_associated_with_project")
    now = _now()
    op = Operation(project_id=project_id, operation_type_id=operation_type_id,
                   property_id=property_id, status="DRAFT", current_workflow_state="DRAFT", created_by=user.id,
                   created_at=now, updated_at=now, version=1, current_version_number=0)
    db.add(op); db.flush()
    if appointment_id is not None:
        appointment = db.get(Appointment, appointment_id)
        if appointment is None: raise NotFoundError("appointment_not_found")
        if appointment.project_id != project_id: raise ValidationError("appointment_project_mismatch")
        db.add(OperationAppointment(appointment_id=appointment.id, operation_id=op.id, created_at=now))
        db.flush()
    return op

def add_party(db: Session, user: User, operation_id: int, person_id: int, role_id: int,
              sequence_no: int = 1, expected_version: int | None = None) -> OperationParty:
    op = db.get(Operation, operation_id)
    if op is None: raise NotFoundError("operation_not_found")
    _require_project_access(db, user, op.project_id, "operation.edit")
    if op.status == "FINALIZED": raise ConflictError("operation_finalized")
    if expected_version is not None and op.version != expected_version: raise ConflictError("stale_operation")
    person, role = db.get(Person, person_id), db.get(PartyRole, role_id)
    if person is None or not person.is_active: raise ValidationError("person_invalid")
    if role is None or not role.active or role.retired_at is not None: raise ValidationError("party_role_invalid")
    now = _now()
    party = OperationParty(operation_id=op.id, person_id=person_id, role_id=role_id, sequence_no=sequence_no,
                           created_at=now, updated_at=now, version=1)
    db.add(party); op.version += 1; op.updated_at = now; db.flush(); return party

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
                           "status": op.status, "workflow_state": op.current_workflow_state},
            "property": None if prop is None else {"property_id": prop.id, "block_tower": prop.block_tower,
                "floor": prop.floor, "orientation": prop.orientation, "unit_number": prop.unit_number,
                "unit_code": prop.unit_code, "plaque_number": prop.plaque_number, "address": prop.address},
            "parties": parties}

def finalize_operation(db: Session, user: User, operation_id: int, expected_version: int | None = None,
                       reason: str | None = None) -> OperationVersion:
    op = db.get(Operation, operation_id)
    if op is None: raise NotFoundError("operation_not_found")
    _require_project_access(db, user, op.project_id, "operation.finalize")
    if op.status == "FINALIZED": raise ConflictError("operation_already_finalized")
    if expected_version is not None and op.version != expected_version: raise ConflictError("stale_operation")
    if op.property_id is None: raise ValidationError("property_required")

    payload = _snapshot(db, op)
    encoded = _canonical(payload)
    now = _now()
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
    db.add(version); db.flush(); return version
