from datetime import datetime
from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base

class Project(Base):
    __tablename__ = "projects"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text())
    status: Mapped[str] = mapped_column(String(32), nullable=False, default='ACTIVE')
    timezone: Mapped[str] = mapped_column(String(64), nullable=False, default='Asia/Tehran')
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

class Person(Base):
    __tablename__ = "persons"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    father_name: Mapped[str | None] = mapped_column(String(100))
    national_id: Mapped[str | None] = mapped_column(String(32))
    mobile: Mapped[str | None] = mapped_column(String(32))
    address: Mapped[str | None] = mapped_column(Text())
    notes: Mapped[str | None] = mapped_column(Text())
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

class Property(Base):
    __tablename__ = "properties"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    block_tower: Mapped[str | None] = mapped_column(String(100))
    floor: Mapped[str | None] = mapped_column(String(32))
    orientation: Mapped[str | None] = mapped_column(String(64))
    unit_number: Mapped[str | None] = mapped_column(String(64))
    unit_code: Mapped[str | None] = mapped_column(String(128))
    plaque_number: Mapped[str | None] = mapped_column(String(64))
    address: Mapped[str | None] = mapped_column(Text())
    notes: Mapped[str | None] = mapped_column(Text())
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

class ProjectPerson(Base):
    __tablename__ = "project_persons"
    project_id: Mapped[int] = mapped_column(ForeignKey('projects.id', ondelete='RESTRICT'), primary_key=True)
    person_id: Mapped[int] = mapped_column(ForeignKey('persons.id', ondelete='RESTRICT'), primary_key=True)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

class ProjectProperty(Base):
    __tablename__ = "project_properties"
    project_id: Mapped[int] = mapped_column(ForeignKey('projects.id', ondelete='RESTRICT'), primary_key=True)
    property_id: Mapped[int] = mapped_column(ForeignKey('properties.id', ondelete='RESTRICT'), primary_key=True)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    context_json: Mapped[str | None] = mapped_column(Text())
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    display_name: Mapped[str] = mapped_column(String(200), nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

class Role(Base):
    __tablename__ = "roles"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text())
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

class Permission(Base):
    __tablename__ = "permissions"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(150), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text())

class RolePermission(Base):
    __tablename__ = "role_permissions"
    role_id: Mapped[int] = mapped_column(ForeignKey('roles.id', ondelete='RESTRICT'), primary_key=True)
    permission_id: Mapped[int] = mapped_column(ForeignKey('permissions.id', ondelete='RESTRICT'), primary_key=True)

class ProjectAccess(Base):
    __tablename__ = "project_access"
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id', ondelete='RESTRICT'), primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey('projects.id', ondelete='RESTRICT'), primary_key=True)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    granted_by: Mapped[int | None] = mapped_column(ForeignKey('users.id', ondelete='RESTRICT'))
    granted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

class UserRole(Base):
    __tablename__ = "user_roles"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id', ondelete='RESTRICT'), nullable=False)
    role_id: Mapped[int] = mapped_column(ForeignKey('roles.id', ondelete='RESTRICT'), nullable=False)
    project_id: Mapped[int | None] = mapped_column(ForeignKey('projects.id', ondelete='RESTRICT'))
    __table_args__ = (UniqueConstraint('user_id', 'role_id', 'project_id', name='uq_user_role_scope'),)

class Session(Base):
    __tablename__ = "sessions"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id', ondelete='RESTRICT'), nullable=False)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))