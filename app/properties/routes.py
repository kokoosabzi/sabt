from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field, model_validator
from sqlalchemy.orm import Session

from app.auth.dependencies import current_user, get_db
from app.db.models import User
from app.properties.service import (
    PropertyNotFoundError, PropertyValidationError, associate_property, create_property, list_properties,
)

router = APIRouter(prefix="/properties", tags=["properties"])


class PropertyCreateRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    project_id: int = Field(ge=1)
    block_tower: str | None = Field(default=None, max_length=100)
    floor: str | None = Field(default=None, max_length=32)
    orientation: str | None = Field(default=None, max_length=64)
    unit_number: str | None = Field(default=None, max_length=64)
    unit_code: str | None = Field(default=None, max_length=128)
    plaque_number: str | None = Field(default=None, max_length=64)
    address: str | None = Field(default=None, max_length=4000)
    notes: str | None = Field(default=None, max_length=4000)

    @model_validator(mode="after")
    def require_identifier(self):
        if not any((self.unit_number, self.unit_code, self.plaque_number)):
            raise ValueError("property_identifier_required")
        return self


@router.get("")
def list_properties_endpoint(
    project_id: int = Query(ge=1),
    q: str | None = Query(default=None, max_length=200),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> dict:
    try:
        properties = list_properties(db, user, project_id=project_id, query=q, limit=limit, offset=offset)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail="Forbidden") from exc
    except PropertyNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"items": [_property_payload(item) for item in properties], "limit": limit, "offset": offset}


@router.post("", status_code=201)
def create_property_endpoint(
    payload: PropertyCreateRequest,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> dict:
    try:
        property_record, possible_duplicates = create_property(
            db, user, project_id=payload.project_id, block_tower=payload.block_tower,
            floor=payload.floor, orientation=payload.orientation, unit_number=payload.unit_number,
            unit_code=payload.unit_code, plaque_number=payload.plaque_number,
            address=payload.address, notes=payload.notes,
        )
        db.commit()
        db.refresh(property_record)
    except PermissionError as exc:
        db.rollback()
        raise HTTPException(status_code=403, detail="Forbidden") from exc
    except PropertyNotFoundError as exc:
        db.rollback()
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except PropertyValidationError as exc:
        db.rollback()
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception:
        db.rollback()
        raise
    return {
        **_property_payload(property_record),
        "possible_duplicate_ids": possible_duplicates,
        "possible_duplicate_warning": bool(possible_duplicates),
    }


@router.post("/{property_id}/projects/{project_id}", status_code=200)
def associate_property_endpoint(
    property_id: int, project_id: int,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> dict:
    try:
        association = associate_property(db, user, project_id=project_id, property_id=property_id)
        db.commit()
        db.refresh(association)
    except PermissionError as exc:
        db.rollback()
        raise HTTPException(status_code=403, detail="Forbidden") from exc
    except PropertyNotFoundError as exc:
        db.rollback()
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception:
        db.rollback()
        raise
    return {"project_id": association.project_id, "property_id": association.property_id, "active": association.active}


def _property_payload(property_record) -> dict:
    return {
        "id": property_record.id, "block_tower": property_record.block_tower,
        "floor": property_record.floor, "orientation": property_record.orientation,
        "unit_number": property_record.unit_number, "unit_code": property_record.unit_code,
        "plaque_number": property_record.plaque_number, "address": property_record.address,
        "notes": property_record.notes, "version": property_record.version,
        "is_active": property_record.is_active,
    }