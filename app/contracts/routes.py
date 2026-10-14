from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth.dependencies import current_user, get_db
from app.contracts.service import (
    ParentContractNotFoundError,
    ParentContractValidationError,
    get_parent_contract_history,
)

router = APIRouter(prefix="/contracts/parent", tags=["contracts"])


@router.get("/{contract_number}/history")
def parent_contract_history(
    contract_number: str,
    user=Depends(current_user),
    db: Session = Depends(get_db),
) -> dict:
    """Return the authorized transfer chain and derived current owner."""
    try:
        return get_parent_contract_history(db, user, contract_number)
    except ParentContractValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except ParentContractNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
