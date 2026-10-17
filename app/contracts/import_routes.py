from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.auth.dependencies import current_user, get_db
from app.contracts.import_service import (
    ContractImportError,
    MAX_UPLOAD_BYTES,
    parse_parent_contract_import,
    preview_parent_contract_import,
)
from app.contracts.numbering import validate_parent_contract_suffix
from app.contracts.service import (
    ParentContractConflictError,
    ParentContractValidationError,
    create_parent_contract,
)
from app.db.models import User

router = APIRouter(prefix="/contracts/parent/import", tags=["contract-import"])


class ImportConfirmation(BaseModel):
    project_id: int
    rows: list[dict[str, Any]] = Field(min_length=1, max_length=2000)


@router.post("/preview")
async def preview_import(
    project_id: int,
    file: UploadFile = File(...),
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> dict:
    try:
        content = await file.read(MAX_UPLOAD_BYTES + 1)
        rows = parse_parent_contract_import(file.filename or "", content)
        return preview_parent_contract_import(db, user, project_id, rows)
    except ContractImportError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    finally:
        await file.close()


@router.post("/validate")
def validate_import_rows(
    payload: ImportConfirmation,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> dict:
    """Revalidate edited preview rows without creating or modifying contracts."""
    try:
        normalized = []
        for index, row in enumerate(payload.rows, start=2):
            try:
                suffix = validate_parent_contract_suffix(str(row.get("suffix", "")).strip())
                person_id = int(row.get("initial_person_id"))
                property_value = row.get("property_id")
                property_id = int(property_value) if property_value not in (None, "") else None
                if person_id <= 0 or (property_id is not None and property_id <= 0):
                    raise ValueError
            except (ValueError, TypeError) as exc:
                raise ContractImportError(f"import_row_invalid:{index}") from exc
            normalized.append({
                "row_number": index,
                "suffix": suffix,
                "initial_person_id": person_id,
                "property_id": property_id,
            })
        return preview_parent_contract_import(db, user, payload.project_id, normalized)
    except (ContractImportError, ValueError, TypeError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc


@router.post("/confirm")
def confirm_import(
    payload: ImportConfirmation,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> dict:
    """Revalidate client-submitted preview rows, then commit all-or-nothing."""
    try:
        normalized = []
        for index, row in enumerate(payload.rows, start=2):
            try:
                suffix = validate_parent_contract_suffix(str(row.get("suffix", "")).strip())
                person_id = int(row.get("initial_person_id"))
                property_value = row.get("property_id")
                property_id = int(property_value) if property_value not in (None, "") else None
                if person_id <= 0 or (property_id is not None and property_id <= 0):
                    raise ValueError
            except (ValueError, TypeError) as exc:
                raise ContractImportError(f"import_row_invalid:{index}") from exc
            normalized.append({
                "row_number": index,
                "suffix": suffix,
                "initial_person_id": person_id,
                "property_id": property_id,
            })
        preview = preview_parent_contract_import(db, user, payload.project_id, normalized)
        if not preview["can_confirm"]:
            raise HTTPException(status_code=422, detail={
                "code": "import_preview_has_errors",
                "issues": preview["issues"],
            })
        created = []
        try:
            # A single outer transaction ensures a failed row leaves no partial import.
            with db.begin_nested():
                for row in normalized:
                    record = create_parent_contract(
                        db, user, payload.project_id, row["suffix"],
                        row["initial_person_id"], row["property_id"],
                    )
                    created.append({
                        "id": record.id,
                        "contract_number": record.contract_number,
                        "suffix": record.suffix,
                    })
            db.commit()
        except Exception:
            db.rollback()
            raise
        return {"status": "created", "project_id": payload.project_id,
                "created_count": len(created), "contracts": created}
    except HTTPException:
        raise
    except (ContractImportError, ValueError, TypeError) as exc:
        db.rollback()
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except PermissionError as exc:
        db.rollback()
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except (ParentContractConflictError, ParentContractValidationError) as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail=str(exc)) from exc
