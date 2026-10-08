# SABT — Database Schema Specification

Version: 0.1
Status: Draft / Architecture Baseline

## 1. Database principles

- V1 database: SQLite.
- ORM: SQLAlchemy.
- Migrations: Alembic.
- Database access occurs only through the FastAPI application.
- All business tables use an internal generated primary key.
- Business identifiers such as contract_number and registration_number are never used as primary keys.
- Timestamps are stored in Gregorian form.
- UI conversion to Jalali is a presentation concern.
- Foreign keys are enabled.
- Transactions are used for multi-step business operations such as Finalize, numbering, restriction override and restore metadata.
- Optimistic concurrency is represented by a version counter on mutable business records.

## 2. Key entities

### projects
Core project records.

Columns:
- id
- code
- name
- description
- status
- branding_config_id (nullable)
- created_at
- updated_at
- version

Constraints:
- code should be unique.
- name should be indexed.

### persons
Central reusable person master records.

Columns:
- id
- first_name
- last_name
- father_name
- national_id
- mobile
- address
- notes
- created_at
- updated_at
- version
- is_active

Indexes:
- national_id
- mobile
- normalized full-name search support

National ID uniqueness must be configurable rather than blindly hard-coded because exceptional data/import cases may exist.

### properties
Central reusable property records.

Columns:
- id
- block_tower
- floor
- orientation
- unit_number
- unit_code
- plaque_number
- address
- notes
- created_at
- updated_at
- version
- is_active

Indexes:
- project_id
- unit_number
- unit_code
- plaque_number

### appointment_types
Global appointment type definitions.

Columns:
- id
- code
- name
- description
- attendance_behavior
- default_duration_minutes
- active
- created_at
- updated_at

attendance_behavior examples:
- ATTENDANCE_ONLY
- ATTENDANCE_AND_START_OPERATION

### appointment_slots / appointment configuration
Appointment tile configuration should be represented as configuration, not as thousands of permanently created empty records.

Configuration may define:
- project_id
- weekday
- start_time
- end_time
- interval_minutes
- active

Actual appointments are stored separately.

### appointments
Columns:
- id
- project_id
- appointment_type_id
- start_at
- end_at
- status
- notes
- created_by
- created_at
- updated_at
- version

Statuses:
- RESERVED
- PRESENT
- NO_SHOW
- CANCELLED
- DONE

A free tile is a calculated availability state, not necessarily a row in appointments.

Indexes:
- project_id + start_at
- status
- appointment_type_id

### operation_types
Global base operation type definitions.

Columns:
- id
- code
- name
- description
- active
- system_defined
- retired_at (nullable)
- created_at
- updated_at

### project_operation_types
Project-specific activation/configuration of an operation type.

Columns:
- id
- project_id
- operation_type_id
- enabled
- config_json
- created_at
- updated_at
- version

Critical configuration is represented through dedicated tables. Opaque config_json may only hold non-critical presentation/configuration data.

Unique:
- project_id + operation_type_id

### project_properties

Project-specific association/context for centrally shared Property records.

Columns:
- project_id
- property_id
- active
- context_json (optional non-critical project context)
- created_at
- updated_at

Unique:
- project_id + property_id

### project_persons

Optional explicit Project association for centrally shared Person records.

Columns:
- project_id
- person_id
- active
- created_at
- updated_at

Unique:
- project_id + person_id

### operations
Central workflow entity.

Columns:
- id
- project_id
- operation_type_id
- appointment_id (nullable)
- status
- current_workflow_state
- property_id (nullable until required by workflow)
- created_by
- finalized_by
- created_at
- updated_at
- finalized_at
- version
- current_version_number

Important:
- One Appointment may have many Operations.
- An Operation may have no Appointment.
- An Operation has zero or one Contract.
- Contract relation must not be duplicated through multiple inconsistent foreign keys.

Recommended ownership:
- contract.operation_id is the authoritative 0..1 relation.
- Avoid operations.contract_id if contract.operation_id already establishes the relationship.

### operation_parties
Associates people with operations through dynamic roles.

Columns:
- id
- operation_id
- person_id
- role_id
- sequence_no
- notes
- created_at
- updated_at
- version

Unique recommendation:
- operation_id + role_id + sequence_no

Duplicate role assignments are allowed because Party Roles are dynamic and a workflow may legitimately require multiple people with the same role.

### party_roles
Admin-defined roles.

Columns:
- id
- code
- name
- description
- active
- system_defined
- created_at
- updated_at

### contract_number_policies

Columns:
- id
- project_id (nullable)
- operation_type_id (nullable)
- uniqueness_scope
- active
- created_at
- updated_at

uniqueness_scope:
- GLOBAL
- PROJECT
- OPERATION_TYPE
- NONE

### contracts
Optional business record generated by an operation.

Columns:
- id
- operation_id
- contract_number
- registration_number
- property_id
- status
- created_at
- updated_at
- finalized_at
- version

Constraints:
- operation_id UNIQUE
- property_id NOT NULL when contract exists
- contract_number uniqueness follows Admin policy and therefore should not be blindly encoded as a single global UNIQUE constraint.

Indexes:
- contract_number
- registration_number
- project scope through operation/project relation

### numbering_states

Atomic sequence state for generated business identifiers.

Columns:
- id
- numbering_policy_id
- scope_key
- current_value
- updated_at
- version

Unique:
- numbering_policy_id + scope_key

Allocation is transactional and must not use MAX()+1.

### operation_versions
Immutable finalized/correction versions.

Columns:
- id
- operation_id
- version_number
- reason
- created_by
- created_at
- finalized_at
- snapshot_json
- hash

Unique:
- operation_id + version_number

Purpose:
Preserve the historical business state without rewriting previous finalized versions.

A normalized snapshot table may be introduced later for high-value fields, but the first architecture permits a canonical immutable JSON snapshot alongside structured core data.

### person_snapshots
Immutable operation-specific person snapshots.

Columns:
- id
- operation_id
- person_id (nullable reference to source master)
- party_id (nullable)
- snapshot_data_json
- created_at
- snapshot_hash

### property_snapshots
Immutable operation-specific property snapshots.

Columns:
- id
- operation_id
- property_id (nullable reference to master)
- snapshot_data_json
- created_at
- snapshot_hash

The snapshot is authoritative for finalized historical reproduction.

### operation_type_required_roles

Defines required Party Roles and cardinality for an Operation Type.

Columns:
- operation_type_id
- party_role_id
- min_count
- max_count (nullable)
- sequence_required

Unique:
- operation_type_id + party_role_id

### operation_type_required_documents

Defines required document types per Operation Type, with project activation/configuration determining applicability.

Columns:
- operation_type_id
- document_type_id
- required
- min_count
- max_count (nullable)

### custom_field_definitions
Metadata definitions.

Columns:
- id
- entity_type
- key
- label
- data_type
- required
- validation_json
- options_json
- display_order
- active
- scope_type
- project_id (nullable)
- operation_type_id (nullable)
- created_at
- updated_at

Supported entity_type candidates:
- PERSON
- PROPERTY
- OPERATION
- CONTRACT
- APPOINTMENT

### custom_field_values
Columns:
- id
- field_definition_id
- entity_type
- entity_id
- value_text
- value_number
- value_boolean
- value_date
- value_datetime
- value_json
- created_at
- updated_at

Exactly one value representation should normally be populated according to the field definition.

Indexes:
- entity_type + entity_id
- field_definition_id

### documents
Document metadata.

Columns:
- id
- project_id
- operation_id (nullable)
- contract_id (nullable)
- document_type
- title
- original_filename
- storage_key
- mime_type
- file_size
- content_hash
- document_number
- document_date
- description
- archived_at
- created_by
- created_at
- updated_at
- version

Rules:
- file bytes are outside SQLite.
- storage_key is relative and stable.
- replacement updates the current file metadata and is audited.
- physical deletion is separate from archive.

### document_types
Configurable document classifications.

Columns:
- id
- code
- name
- description
- active
- allowed_mime_types
- created_at
- updated_at

### audit_events
Central audit log.

Columns:
- id
- actor_user_id
- action
- entity_type
- entity_id
- project_id
- timestamp
- reason
- before_json
- after_json
- metadata_json
- severity

Indexes:
- timestamp
- actor_user_id
- entity_type + entity_id
- project_id

### restriction_rules
Contract-oriented block/warning rules.

Columns:
- id
- name
- code
- active
- severity
- action
- message
- override_permission
- effective_from
- effective_to
- created_by
- created_at
- updated_at

### contract_restrictions
Imported/managed restriction records.

Columns:
- id
- restriction_rule_id
- contract_number
- source_batch_id
- active
- note
- created_at
- updated_at
- unblocked_at
- unblocked_by

Indexes:
- contract_number
- active
- restriction_rule_id

### restriction_import_batches
Import audit/control.

Columns:
- id
- source_filename
- source_type
- row_count
- success_count
- error_count
- imported_by
- imported_at
- mapping_json
- validation_summary_json

### users
Columns:
- id
- username
- password_hash
- display_name
- active
- created_at
- updated_at
- last_login_at
- version

### roles
Columns:
- id
- code
- name
- description
- active
- created_at
- updated_at

### permissions
Columns:
- id
- code
- name
- description

### role_permissions
Many-to-many relation.

Columns:
- role_id
- permission_id

Unique:
- role_id + permission_id

### project_access

Explicit Project access independent from Role assignment.

Columns:
- user_id
- project_id
- active
- granted_by
- granted_at
- revoked_at
- version

Unique active access per user/project.

### user_roles
Many-to-many relation.

Columns:
- user_id
- role_id
- project_id (nullable)

A nullable project_id permits global roles and project-scoped assignments.

### operation_type_workflows

Explicit workflow configuration per Operation Type.

Columns:
- id
- operation_type_id
- project_id (nullable)
- state_code
- sequence_no
- active
- config_json (presentation/non-critical only)

### print_templates
Columns:
- id
- project_id (nullable)
- operation_type_id (nullable)
- name
- page_size
- orientation
- config_json
- active
- created_by
- created_at
- updated_at
- version

The config contains positioned elements:
- field
- static text
- logo
- QR
- line/box where supported

Coordinates are stored in mm at the template domain layer.

### generated_documents
Tracks generated PDFs.

Columns:
- id
- project_id
- operation_id
- contract_id (nullable)
- template_id
- storage_key
- content_hash
- generated_by
- generated_at
- metadata_json

### logos / branding
Branding should be metadata-driven.

Possible tables:
- branding_profiles
- branding_assets

A project may reference a branding profile. Templates can choose system, project or template-specific logo assets.

### numbering_policies
Generic configuration for generated business identifiers.

Columns:
- id
- project_id (nullable)
- operation_type_id (nullable)
- identifier_type
- scope
- prefix
- sequence_width
- reset_policy
- format_template
- active
- created_at
- updated_at

The actual next-number allocation must be atomic. Allocation state is stored in numbering_states.

### reminders
Columns:
- id
- project_id (nullable)
- name
- trigger_type
- target_type
- rule_json
- message_template
- severity
- active
- created_at
- updated_at

### notification_events
Columns:
- id
- reminder_id
- recipient_user_id
- appointment_id (nullable)
- operation_id (nullable)
- triggered_at
- read_at
- dismissed_at
- payload_json

## 3. Referential integrity

- Enable SQLite foreign keys.
- Prefer RESTRICT for deletion of business records referenced by finalized records.
- Use logical archival instead of deleting business records.
- Cascading deletes should be limited to configuration/association rows where historical data cannot be lost.
- Finalized snapshots and audit events must never be cascade-deleted by ordinary business operations.

## 4. Date/time

Persist:
- date/time in Gregorian representation.
- timestamps in a consistent timezone strategy.
Display:
- Jalali date in Persian UI/forms/reports.
- 24-hour local time.

Recommended V1 policy: store timezone-aware UTC instants internally; Project has an explicit presentation/business timezone; UI converts to Persian/Jalali using the Project timezone. Server-local timezone is never an implicit business rule.

## 5. Snapshot contract

The immutable OperationVersion snapshot must contain at minimum:
- operation core identity and type
- project identity
- workflow/finalization state
- parties, role assignments and party snapshot data
- property context snapshot
- contract data when present
- registration and contract numbers when present
- relevant custom-field values
- exact template revision reference
- immutable branding asset references/content hashes required for generated output
- QR configuration/version required for reproduction

Person/Property master rows are references only and are never sufficient to reconstruct finalized historical truth.

## 6. IDs

Use generated internal IDs. UUIDs are preferred if multi-machine/offline synchronization may later become relevant; otherwise integer IDs are acceptable for V1. The final implementation decision should be made before migration generation.

## 7. Indexing strategy

Minimum indexes:
- persons.national_id
- persons.mobile
- properties.project_id/unit_number/unit_code/plaque_number
- appointments.project_id/start_at/status
- operations.project_id/status/created_at
- operation_parties.person_id
- contracts.contract_number
- contracts.registration_number
- documents.operation_id
- documents.contract_id
- documents.content_hash
- audit_events.timestamp/entity/project
- contract_restrictions.contract_number/active

Composite indexes should be added based on actual query plans after the first UI/search implementation.

## 8. Transaction boundaries

The following must be atomic transactions:
- Finalize Operation
- Create Contract + allocate Registration Number
- Restriction override/unblock
- Restore bookkeeping metadata
- Correction version creation
- Sensitive document replacement metadata update

## 9. SQLite-specific requirements

- WAL mode is recommended for server-side concurrent reads/writes.
- Busy timeout should be configured.
- Foreign keys must be enabled on every connection.
- SQLite must not be exposed as a shared network file.
- Backup must use a safe database backup mechanism rather than copying a live DB file blindly.

## 10. Migration policy

Alembic migrations are mandatory even for V1.
Never modify the production schema manually.
Every schema change must have:
- migration
- downgrade strategy where practical
- data migration if required
- test coverage for critical constraints
