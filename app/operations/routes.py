from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth.dependencies import current_user, get_db
from app.operations.service import (
    ConflictError,
    NotFoundError,
    ValidationError,
    transition_operation,
)

router = APIRouter(prefix="/operations", tags=["operations"])


class OperationTransitionRequest(BaseModel):
    target_state: str = Field(min_length=1, max_length=64)
    expected_version: int = Field(ge=1)
    reason: str | None = Field(default=None, max_length=2000)


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
