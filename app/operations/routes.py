from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.auth.dependencies import current_user, get_db
from app.auth.authorization import AuthorizationContext, authorize
from app.db.models import Operation, OperationParty, OperationType, ParentContract, PartyRole, Person, Project
from app.operations.service import (
    ConflictError,
    NotFoundError,
    ValidationError,
    add_party,
    create_operation,
    finalize_operation,
    transition_operation,
)

router = APIRouter(prefix="/operations", tags=["operations"])


class OperationCreateRequest(BaseModel):
    project_id: int = Field(ge=1)
    operation_type_id: int = Field(ge=1)
    property_id: int | None = Field(default=None, ge=1)
    appointment_id: int | None = Field(default=None, ge=1)
    parent_contract_id: int | None = Field(default=None, ge=1)


class OperationPartyCreateRequest(BaseModel):
    person_id: int = Field(ge=1)
    role_id: int = Field(ge=1)
    sequence_no: int = Field(default=1, ge=1)
    expected_version: int = Field(ge=1)


class OperationTransitionRequest(BaseModel):
    target_state: str = Field(min_length=1, max_length=64)
    expected_version: int = Field(ge=1)
    reason: str | None = Field(default=None, max_length=2000)


class OperationFinalizeRequest(BaseModel):
    expected_version: int = Field(ge=1)
    reason: str | None = Field(default=None, max_length=2000)




@router.post("", status_code=201)
def create_operation_endpoint(
    payload: OperationCreateRequest,
    user=Depends(current_user),
    db: Session = Depends(get_db),
) -> dict:
    """Create a draft operation within the requested project."""
    try:
        operation = create_operation(
            db,
            user,
            payload.project_id,
            payload.operation_type_id,
            property_id=payload.property_id,
            appointment_id=payload.appointment_id,
            parent_contract_id=payload.parent_contract_id,
        )
        db.commit()
        db.refresh(operation)
    except NotFoundError as exc:
        db.rollback()
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except PermissionError as exc:
        db.rollback()
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ConflictError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ValidationError as exc:
        db.rollback()
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception:
        db.rollback()
        raise

    return {
        "operation_id": operation.id,
        "project_id": operation.project_id,
        "operation_type_id": operation.operation_type_id,
        "property_id": operation.property_id,
        "parent_contract_id": operation.parent_contract_id,
        "status": operation.status,
        "workflow_state": operation.current_workflow_state,
        "version": operation.version,
        "created_at": operation.created_at.isoformat(),
    }


@router.post("/{operation_id}/transition")
def transition_operation_endpoint(
    operation_id: int,
    payload: OperationTransitionRequest,
    user=Depends(current_user),
    db: Session = Depends(get_db),
) -> dict:
    """Advance an operation to the next configured state.

    The route owns the transaction boundary: successful transitions commit;
    all rejected transitions roll back without persisting partial changes.
    """
    try:
        operation = transition_operation(
            db,
            user,
            operation_id,
            payload.target_state,
            payload.expected_version,
            payload.reason,
        )
        db.commit()
        db.refresh(operation)
    except NotFoundError as exc:
        db.rollback()
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except PermissionError as exc:
        db.rollback()
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ConflictError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ValidationError as exc:
        db.rollback()
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception:
        db.rollback()
        raise

    return {
        "operation_id": operation.id,
        "project_id": operation.project_id,
        "status": operation.status,
        "workflow_state": operation.current_workflow_state,
        "version": operation.version,
        "updated_at": operation.updated_at.isoformat(),
    }


@router.post("/{operation_id}/finalize")
def finalize_operation_endpoint(
    operation_id: int,
    payload: OperationFinalizeRequest,
    user=Depends(current_user),
    db: Session = Depends(get_db),
) -> dict:
    """Finalize a ready operation and commit snapshots, numbering and events atomically."""
    try:
        version = finalize_operation(db, user, operation_id, payload.expected_version, payload.reason)
        db.commit()
        db.refresh(version)
        operation = db.get(Operation, operation_id)
        db.refresh(operation)
    except NotFoundError as exc:
        db.rollback()
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except PermissionError as exc:
        db.rollback()
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ConflictError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ValidationError as exc:
        db.rollback()
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception:
        db.rollback()
        raise

    return {
        "operation_id": operation.id,
        "status": operation.status,
        "workflow_state": operation.current_workflow_state,
        "version": operation.version,
        "operation_version_id": version.id,
        "version_number": version.version_number,
        "child_contract_number": operation.child_contract_number,
        "transfer_sequence": operation.transfer_sequence,
        "finalized_at": operation.finalized_at.isoformat() if operation.finalized_at else None,
    }




@router.post("/{operation_id}/parties", status_code=201)
def add_operation_party_endpoint(
    operation_id: int,
    payload: OperationPartyCreateRequest,
    user=Depends(current_user),
    db: Session = Depends(get_db),
) -> dict:
    """Add a project-associated person to a draft operation."""
    try:
        party = add_party(
            db,
            user,
            operation_id,
            payload.person_id,
            payload.role_id,
            payload.sequence_no,
            expected_version=payload.expected_version,
        )
        db.commit()
        db.refresh(party)
    except NotFoundError as exc:
        db.rollback()
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except PermissionError as exc:
        db.rollback()
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ConflictError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ValidationError as exc:
        db.rollback()
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception:
        db.rollback()
        raise

    return {
        "party_id": party.id,
        "project_id": party.project_id,
        "operation_id": party.operation_id,
        "person_id": party.person_id,
        "role_id": party.role_id,
        "sequence_no": party.sequence_no,
        "version": party.version,
        "created_at": party.created_at.isoformat(),
    }




@router.get("/{operation_id}/parties")
def list_operation_parties_endpoint(
    operation_id: int,
    user=Depends(current_user),
    db: Session = Depends(get_db),
) -> dict:
    """List parties attached to an operation after project-scoped view authorization."""
    operation = db.get(Operation, operation_id)
    if operation is None:
        raise HTTPException(status_code=404, detail="operation_not_found")
    try:
        authorize(
            db,
            user,
            "operation.view",
            AuthorizationContext(project_id=operation.project_id),
        )
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc

    parties = db.scalars(
        select(OperationParty)
        .where(
            OperationParty.operation_id == operation.id,
            OperationParty.project_id == operation.project_id,
        )
        .order_by(OperationParty.role_id, OperationParty.sequence_no, OperationParty.id)
    ).all()
    result = []
    for party in parties:
        person = db.get(Person, party.person_id)
        role = db.get(PartyRole, party.role_id)
        result.append({
            "party_id": party.id,
            "person_id": party.person_id,
            "first_name": person.first_name if person else None,
            "last_name": person.last_name if person else None,
            "role_id": party.role_id,
            "role_code": role.code if role else None,
            "role_name": role.name if role else None,
            "sequence_no": party.sequence_no,
            "version": party.version,
        })
    return {"operation_id": operation.id, "parties": result}


@router.get("/{operation_id}")
def get_operation_endpoint(
    operation_id: int,
    user=Depends(current_user),
    db: Session = Depends(get_db),
) -> dict:
    """Return a single operation only when the caller has project-scoped view access."""
    operation = db.get(Operation, operation_id)
    if operation is None:
        raise HTTPException(status_code=404, detail="operation_not_found")
    try:
        authorize(
            db,
            user,
            "operation.view",
            AuthorizationContext(project_id=operation.project_id),
        )
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc

    return {
        "operation_id": operation.id,
        "project_id": operation.project_id,
        "operation_type_id": operation.operation_type_id,
        "property_id": operation.property_id,
        "parent_contract_id": operation.parent_contract_id,
        "status": operation.status,
        "workflow_state": operation.current_workflow_state,
        "version": operation.version,
        "created_at": operation.created_at.isoformat(),
        "updated_at": operation.updated_at.isoformat(),
        "finalized_at": operation.finalized_at.isoformat() if operation.finalized_at else None,
    }



@router.get("")
def list_operations_endpoint(
    project_id: int = Query(ge=1),
    status: str | None = Query(default=None, min_length=1, max_length=32),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    user=Depends(current_user),
    db: Session = Depends(get_db),
) -> dict:
    """List project operations for an authorized resumable workflow workspace."""
    project = db.get(Project, project_id)
    if project is None or project.status != "ACTIVE":
        raise HTTPException(status_code=404, detail="project_not_found")
    try:
        authorize(
            db,
            user,
            "operation.view",
            AuthorizationContext(project_id=project_id),
        )
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail="forbidden") from exc

    conditions = [Operation.project_id == project_id]
    if status is not None:
        conditions.append(Operation.status == status)
    total = db.scalar(
        select(func.count()).select_from(Operation).where(*conditions)
    ) or 0
    rows = db.execute(
        select(Operation, OperationType.name, ParentContract.contract_number)
        .join(OperationType, OperationType.id == Operation.operation_type_id)
        .outerjoin(
            ParentContract,
            (ParentContract.id == Operation.parent_contract_id)
            & (ParentContract.project_id == Operation.project_id),
        )
        .where(*conditions)
        .order_by(Operation.created_at.desc(), Operation.id.desc())
        .offset(offset)
        .limit(limit)
    ).all()
    return {
        "project_id": project_id,
        "pagination": {
            "limit": limit,
            "offset": offset,
            "total": total,
            "has_more": offset + len(rows) < total,
        },
        "items": [
            {
                "operation_id": operation.id,
                "operation_type_id": operation.operation_type_id,
                "operation_type_name": operation_type_name,
                "property_id": operation.property_id,
                "parent_contract_id": operation.parent_contract_id,
                "parent_contract_number": parent_contract_number,
                "child_contract_number": operation.child_contract_number,
                "transfer_sequence": operation.transfer_sequence,
                "status": operation.status,
                "workflow_state": operation.current_workflow_state,
                "version": operation.version,
                "created_at": operation.created_at.isoformat(),
                "updated_at": operation.updated_at.isoformat(),
                "finalized_at": operation.finalized_at.isoformat() if operation.finalized_at else None,
            }
            for operation, operation_type_name, parent_contract_number in rows
        ],
    }
