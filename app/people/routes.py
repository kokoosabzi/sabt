from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from app.auth.dependencies import current_user, get_db
from app.db.models import User
from app.people.service import (
    PersonNotFoundError, PersonValidationError, associate_person, create_person, list_people,
)

router = APIRouter(prefix="/people", tags=["people"])


class PersonCreateRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    project_id: int = Field(ge=1)
    first_name: str = Field(min_length=1, max_length=100)
    last_name: str = Field(min_length=1, max_length=100)
    father_name: str | None = Field(default=None, max_length=100)
    national_id: str | None = Field(default=None, max_length=32)
    mobile: str | None = Field(default=None, max_length=32)
    address: str | None = Field(default=None, max_length=4000)
    notes: str | None = Field(default=None, max_length=4000)


@router.get("")
def list_people_endpoint(
    project_id: int = Query(ge=1),
    q: str | None = Query(default=None, max_length=200),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> dict:
    try:
        people = list_people(db, user, project_id=project_id, query=q, limit=limit, offset=offset)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail="Forbidden") from exc
    except PersonNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"items": [_person_payload(person) for person in people], "limit": limit, "offset": offset}


@router.post("", status_code=201)
def create_person_endpoint(
    payload: PersonCreateRequest,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> dict:
    try:
        person, possible_duplicates = create_person(
            db, user, project_id=payload.project_id, first_name=payload.first_name,
            last_name=payload.last_name, father_name=payload.father_name,
            national_id=payload.national_id, mobile=payload.mobile,
            address=payload.address, notes=payload.notes,
        )
        db.commit()
        db.refresh(person)
    except PermissionError as exc:
        db.rollback()
        raise HTTPException(status_code=403, detail="Forbidden") from exc
    except PersonNotFoundError as exc:
        db.rollback()
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except PersonValidationError as exc:
        db.rollback()
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception:
        db.rollback()
        raise
    return {
        **_person_payload(person),
        "possible_duplicate_ids": possible_duplicates,
        "possible_duplicate_warning": bool(possible_duplicates),
    }


@router.post("/{person_id}/projects/{project_id}", status_code=200)
def associate_person_endpoint(
    person_id: int, project_id: int,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> dict:
    try:
        association = associate_person(db, user, project_id=project_id, person_id=person_id)
        db.commit()
        db.refresh(association)
    except PermissionError as exc:
        db.rollback()
        raise HTTPException(status_code=403, detail="Forbidden") from exc
    except PersonNotFoundError as exc:
        db.rollback()
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception:
        db.rollback()
        raise
    return {"project_id": association.project_id, "person_id": association.person_id, "active": association.active}


def _person_payload(person) -> dict:
    return {
        "id": person.id, "first_name": person.first_name, "last_name": person.last_name,
        "father_name": person.father_name, "national_id": person.national_id,
        "mobile": person.mobile, "address": person.address, "notes": person.notes,
        "version": person.version, "is_active": person.is_active,
    }