from __future__ import annotations

from datetime import datetime, timezone
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.auth.authorization import AuthorizationContext, authorize
from app.db.models import Project, ProjectProperty, Property, User


class PropertyError(Exception):
    pass


class PropertyNotFoundError(PropertyError):
    pass


class PropertyValidationError(PropertyError):
    pass


def _project(db: Session, project_id: int) -> Project:
    project = db.get(Project, project_id)
    if project is None or project.status != "ACTIVE":
        raise PropertyNotFoundError("project_not_found")
    return project


def create_property(
    db: Session, user: User, *, project_id: int, block_tower: str | None = None,
    floor: str | None = None, orientation: str | None = None, unit_number: str | None = None,
    unit_code: str | None = None, plaque_number: str | None = None, address: str | None = None,
    notes: str | None = None,
) -> tuple[Property, list[int]]:
    authorize(db, user, "property.create", AuthorizationContext(project_id=project_id))
    _project(db, project_id)
    unit_number = unit_number.strip() if unit_number and unit_number.strip() else None
    unit_code = unit_code.strip() if unit_code and unit_code.strip() else None
    plaque_number = plaque_number.strip() if plaque_number and plaque_number.strip() else None
    if not any((unit_number, unit_code, plaque_number)):
        raise PropertyValidationError("property_identifier_required")
    duplicate_conditions = []
    if unit_code:
        duplicate_conditions.append(Property.unit_code == unit_code)
    if unit_number:
        duplicate_conditions.append(Property.unit_number == unit_number)
    if plaque_number:
        duplicate_conditions.append(Property.plaque_number == plaque_number)
    possible_duplicates: list[int] = []
    if duplicate_conditions:
        possible_duplicates = list(db.scalars(
            select(Property.id).join(ProjectProperty, ProjectProperty.property_id == Property.id).where(
                ProjectProperty.project_id == project_id, ProjectProperty.active.is_(True),
                Property.is_active.is_(True), or_(*duplicate_conditions),
            ).order_by(Property.id)
        ).all())
    now = datetime.now(timezone.utc)
    property_record = Property(
        block_tower=block_tower.strip() if block_tower and block_tower.strip() else None,
        floor=floor.strip() if floor and floor.strip() else None,
        orientation=orientation.strip() if orientation and orientation.strip() else None,
        unit_number=unit_number, unit_code=unit_code, plaque_number=plaque_number,
        address=address.strip() if address and address.strip() else None,
        notes=notes.strip() if notes and notes.strip() else None,
        created_at=now, updated_at=now, version=1, is_active=True,
    )
    db.add(property_record)
    db.flush()
    db.add(ProjectProperty(project_id=project_id, property_id=property_record.id, active=True, created_at=now, updated_at=now))
    db.flush()
    return property_record, possible_duplicates


def list_properties(db: Session, user: User, *, project_id: int, query: str | None = None, limit: int = 50, offset: int = 0) -> list[Property]:
    authorize(db, user, "property.view", AuthorizationContext(project_id=project_id))
    _project(db, project_id)
    stmt = select(Property).join(ProjectProperty, ProjectProperty.property_id == Property.id).where(
        ProjectProperty.project_id == project_id, ProjectProperty.active.is_(True), Property.is_active.is_(True),
    )
    normalized = query.strip() if query and query.strip() else None
    if normalized:
        pattern = f"%{normalized}%"
        stmt = stmt.where(or_(
            Property.block_tower.ilike(pattern), Property.floor.ilike(pattern),
            Property.orientation.ilike(pattern), Property.unit_number.ilike(pattern),
            Property.unit_code.ilike(pattern), Property.plaque_number.ilike(pattern),
            Property.address.ilike(pattern),
        ))
    return list(db.scalars(stmt.order_by(Property.block_tower, Property.floor, Property.unit_number, Property.id).limit(limit).offset(offset)).all())


def associate_property(db: Session, user: User, *, project_id: int, property_id: int) -> ProjectProperty:
    authorize(db, user, "property.edit", AuthorizationContext(project_id=project_id))
    _project(db, project_id)
    property_record = db.get(Property, property_id)
    if property_record is None or not property_record.is_active:
        raise PropertyNotFoundError("property_not_found")
    association = db.get(ProjectProperty, (project_id, property_id))
    now = datetime.now(timezone.utc)
    if association is None:
        association = ProjectProperty(project_id=project_id, property_id=property_id, active=True, created_at=now, updated_at=now)
        db.add(association)
    else:
        association.active = True
        association.updated_at = now
    db.flush()
    return association