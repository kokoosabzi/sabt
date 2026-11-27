from __future__ import annotations

from datetime import datetime, timezone
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.auth.authorization import AuthorizationContext, authorize
from app.db.models import Person, Project, ProjectPerson, User


class PersonError(Exception):
    pass


class PersonNotFoundError(PersonError):
    pass


class PersonValidationError(PersonError):
    pass


def _project(db: Session, project_id: int) -> Project:
    project = db.get(Project, project_id)
    if project is None or project.status != "ACTIVE":
        raise PersonNotFoundError("project_not_found")
    return project


def create_person(
    db: Session, user: User, *, project_id: int, first_name: str, last_name: str,
    father_name: str | None = None, national_id: str | None = None,
    mobile: str | None = None, address: str | None = None, notes: str | None = None,
) -> tuple[Person, list[int]]:
    authorize(db, user, "person.create", AuthorizationContext(project_id=project_id))
    _project(db, project_id)
    first_name = first_name.strip()
    last_name = last_name.strip()
    if not first_name or not last_name:
        raise PersonValidationError("person_name_required")
    national_id = national_id.strip() if national_id and national_id.strip() else None
    mobile = mobile.strip() if mobile and mobile.strip() else None
    possible_duplicates: list[int] = []
    if national_id:
        possible_duplicates = list(db.scalars(
            select(Person.id).join(ProjectPerson, ProjectPerson.person_id == Person.id).where(
                ProjectPerson.project_id == project_id, ProjectPerson.active.is_(True),
                Person.is_active.is_(True), Person.national_id == national_id,
            ).order_by(Person.id)
        ).all())
    now = datetime.now(timezone.utc)
    person = Person(
        first_name=first_name, last_name=last_name,
        father_name=father_name.strip() if father_name and father_name.strip() else None,
        national_id=national_id, mobile=mobile,
        address=address.strip() if address and address.strip() else None,
        notes=notes.strip() if notes and notes.strip() else None,
        created_at=now, updated_at=now, version=1, is_active=True,
    )
    db.add(person)
    db.flush()
    db.add(ProjectPerson(project_id=project_id, person_id=person.id, active=True, created_at=now, updated_at=now))
    db.flush()
    return person, possible_duplicates


def list_people(db: Session, user: User, *, project_id: int, query: str | None = None, limit: int = 50, offset: int = 0) -> list[Person]:
    authorize(db, user, "person.view", AuthorizationContext(project_id=project_id))
    _project(db, project_id)
    stmt = select(Person).join(ProjectPerson, ProjectPerson.person_id == Person.id).where(
        ProjectPerson.project_id == project_id, ProjectPerson.active.is_(True), Person.is_active.is_(True),
    )
    normalized = query.strip() if query and query.strip() else None
    if normalized:
        pattern = f"%{normalized}%"
        stmt = stmt.where(or_(
            Person.first_name.ilike(pattern), Person.last_name.ilike(pattern),
            Person.father_name.ilike(pattern), Person.national_id.ilike(pattern), Person.mobile.ilike(pattern),
        ))
    return list(db.scalars(stmt.order_by(Person.last_name, Person.first_name, Person.id).limit(limit).offset(offset)).all())


def associate_person(db: Session, user: User, *, project_id: int, person_id: int) -> ProjectPerson:
    authorize(db, user, "person.edit", AuthorizationContext(project_id=project_id))
    _project(db, project_id)
    person = db.get(Person, person_id)
    if person is None or not person.is_active:
        raise PersonNotFoundError("person_not_found")
    association = db.get(ProjectPerson, (project_id, person_id))
    now = datetime.now(timezone.utc)
    if association is None:
        association = ProjectPerson(project_id=project_id, person_id=person_id, active=True, created_at=now, updated_at=now)
        db.add(association)
    else:
        association.active = True
        association.updated_at = now
    db.flush()
    return association