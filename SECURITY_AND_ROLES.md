# SECURITY_AND_ROLES.md

## 1. Purpose

This document defines the V1 security, identity, role, permission, authorization, project-access, document-access, audit, and sensitive-action architecture.

The security model must protect business records without turning SABT into an unnecessarily complex enterprise IAM platform.

The authoritative security boundary is the FastAPI backend. The browser/client is never trusted to enforce authorization by itself.

## 2. Security Principles

1. Authentication identifies the user; authorization decides what the user may do.
2. Every protected API request is authorized server-side.
3. Permissions are explicit and deny-by-default.
4. Project access is a first-class authorization dimension.
5. Document access follows project access plus document/permission rules.
6. Sensitive actions require explicit permissions and appropriate audit.
7. Finalized business records are immutable under normal permissions.
8. Privileged correction is a controlled workflow, not ordinary editing.
9. No user may gain access merely by guessing an ID or URL.
10. Internal IDs are not authorization tokens.
11. Audit records are append-oriented and protected from ordinary user modification.
12. Authorization failures must not reveal unnecessary information.
13. Security-sensitive operations must be transactional where required.
14. Configuration changes affecting permissions or security must themselves be audited.
15. V1 should remain understandable and maintainable for a local/LAN deployment.

## 3. Security Boundary

Client -> HTTP -> FastAPI -> Authentication -> Authorization -> Application Services -> SQLAlchemy -> SQLite / Filesystem

Only the backend may directly access SQLite, managed document storage, generated PDF storage, template storage, branding storage, backup storage, and signing secrets.

The frontend receives only data authorized for the current user.

The SQLite file must never be opened directly by clients.

## 4. Authentication

V1 requires authenticated users for protected business operations.

Authentication should provide:

- unique username/login identifier
- password authentication
- secure password hashing
- active/disabled state
- last-login metadata
- session/token lifecycle
- logout/revocation behavior
- optional password reset workflow later

Passwords must never be stored in plaintext.

Password hashes must use a modern password hashing algorithm appropriate for Python, with configurable work factor.

## 5. Session Security

The application should use server-controlled session/token validation.

Requirements:

- bounded authenticated-session lifetime
- logout invalidation according to selected mechanism
- disabled users cannot create new sessions
- optional recent-authentication requirement for sensitive actions
- unpredictable session identifiers
- credentials never in URLs
- Secure/HttpOnly/SameSite cookie settings when cookies are used

The architecture should permit HTTPS later without changing authorization design.

## 6. Users

Conceptual users entity:

- id
- username/login
- display_name
- password_hash
- active
- last_login_at
- created_at
- updated_at
- version

Optional future fields:

- phone
- email
- locale
- timezone
- profile preferences

Prefer disabling/archive semantics instead of deleting users referenced by audit history.

## 7. Roles

A Role is a named collection of permissions.

Possible base roles:

- Administrator
- Project Manager
- Operator
- Reviewer
- Read Only

These are seed examples, not a fixed final policy.

A role should have:

- id
- name
- code
- description
- active
- system_role flag where applicable
- created_at
- updated_at
- version

System/base roles may be protected from destructive modification.

## 8. Permissions

Permissions are atomic capabilities.

Suggested namespace:

### Dashboard
- dashboard.view

### Projects
- project.view
- project.create
- project.edit
- project.archive
- project.manage_access

### People
- person.view
- person.create
- person.edit
- person.archive

### Properties
- property.view
- property.create
- property.edit
- property.archive

### Appointments
- appointment.view
- appointment.create
- appointment.edit
- appointment.reserve
- appointment.present
- appointment.no_show
- appointment.cancel
- appointment.complete
- appointment.manage_types
- appointment.manage_slots
- appointment.manage_reminders

### Operations
- operation.view
- operation.create
- operation.edit
- operation.submit
- operation.review
- operation.finalize
- operation.request_correction
- operation.approve_correction
- operation.apply_correction
- operation.override
- operation.archive

### Contracts
- contract.view
- contract.create
- contract.edit
- contract.archive
- contract.override_restriction

### Documents
- document.view
- document.upload
- document.replace
- document.archive
- document.delete_physical
- document.download

### Restrictions
- restriction.view
- restriction.import
- restriction.manage_rules
- restriction.override
- restriction.unblock

### Templates / Printing
- template.view
- template.create
- template.edit
- template.validate
- template.activate
- template.deactivate
- template.archive
- template.preview
- template.generate
- template.print
- template.manage_assets

### Users / Roles
- user.view
- user.create
- user.edit
- user.disable
- role.view
- role.create
- role.edit
- role.assign

### Audit
- audit.view
- audit.export
- audit.configure

### Backup / Restore
- backup.view
- backup.create
- backup.restore
- backup.configure

### System
- settings.view
- settings.edit

The final catalog should be centralized in code/configuration and seeded through migrations.

## 9. Permission Semantics

Permissions are actions, not UI buttons.

For example, operation.finalize means the authenticated principal is authorized to execute the server-side finalization use case.

It does not merely mean that the Finalize button should be visible.

The backend must check authorization at the service/use-case boundary.

UI visibility is only a usability optimization.

## 10. Role Assignment

A user may have multiple roles. Roles may be global or project-scoped.

Recommended relations:

- users
- roles
- user_roles
- permissions
- role_permissions

Effective permissions are the union of permissions granted by active roles, subject to project scope and explicit authorization rules.

V1 should avoid complex deny-overrides-union semantics unless a real requirement emerges.

Default model:

- permissions are granted through roles
- no explicit deny permission
- no permission means denied

## 11. Project Scope

Because SABT supports multiple Projects with shared People and Properties, authorization must distinguish:

- global/system permissions
- project-scoped permissions

A user may be:

- global administrator
- member of selected Projects
- restricted to one Project
- allowed to work in several Projects

Conceptual project_access entity:

- user_id
- project_id
- active
- active
- granted_by
- granted_at
- revoked_at
- version

Project access is not the same thing as a Role.

Role says what a user may do.
Project access says where that capability may be exercised.
A project-scoped role is effective only when the user has active Project access.

## 12. Global vs Project Permissions

Permissions should declare their scope.

Global examples:

- user.create
- role.edit
- backup.restore
- settings.edit
- audit.configure

Project-scoped examples:

- operation.create
- operation.edit
- operation.finalize
- appointment.reserve
- document.upload
- template.activate

A project-scoped permission succeeds only if:

1. user has the permission through an active role
2. user has access to the target Project
3. target entity belongs to that Project
4. additional entity/document authorization passes

A global permission may operate across Projects only when explicitly defined as global.

## 13. Shared People and Properties

People and Properties are central reusable entities.

Project membership must not automatically expose all global Person/Property records.

Recommended policy:

- a user with Project access can view Person/Property data referenced by authorized records in that Project
- global Person/Property administration requires explicit global or appropriate project-level permission
- search applies the same authorization filters
- direct ID lookup also applies authorization

This prevents shared master data from becoming a cross-Project data leak.

## 14. Operation Authorization

An Operation belongs to a Project.

Before any protected Operation action:

1. authenticate user
2. load Operation
3. determine Project
4. verify Project access
5. verify required permission
6. verify Operation state
7. verify additional business rules
8. execute transaction

Examples:

- viewing requires operation.view
- editing a Draft requires operation.edit
- finalization requires operation.finalize
- correction approval requires operation.approve_correction

Knowing an ID is never sufficient for access.

## 15. Permission and Workflow State

Authorization and workflow state are separate checks.

A user may have operation.edit, but a Finalized Operation is still not normally editable.

General model:

Allowed = Authentication + Permission + ProjectAccess + EntityAccess + WorkflowState + BusinessRules

This pattern applies to sensitive actions.

## 16. Finalization Security

Finalization is a high-value action.

Before finalization:

- verify Project access
- verify operation.finalize
- verify optimistic version
- verify workflow state
- validate required fields
- validate required parties
- validate required documents
- evaluate restrictions
- validate numbering policy
- create immutable final snapshot
- allocate registration number atomically if applicable
- create audit event
- commit as one logical transaction

No ordinary user may directly mutate a finalized record.

## 17. Correction Security

Corrections use:

Finalized -> Correction Request -> Approval -> New Version -> Finalization

Recommended permissions:

- operation.request_correction
- operation.approve_correction
- operation.apply_correction

The requester should not automatically be allowed to approve their own correction unless explicitly configured.

Default posture favors separation of duties.

Every correction request and approval is audited.

## 18. Override Permissions

High-risk override actions require explicit permissions.

Examples:

- restriction override
- numbering override
- workflow override
- privileged finalization override
- physical document deletion
- restore

Suggested permissions:

- operation.override
- contract.override_restriction
- restriction.override
- document.delete_physical
- backup.restore

Override actions require:

- permission
- reason
- actor
- timestamp
- affected entity
- audit event

Normal workflow remains preferred whenever possible.

## 19. Document Authorization

Required rule:

DocumentAccess = ProjectAccess + Role/Permission + EntityContext

At minimum:

1. identify owning Project/context
2. verify Project access
3. verify requested document permission
4. verify access to parent entity
5. allow only requested action

Examples:

- document.view for metadata/file viewing
- document.download for file download
- document.replace for replacement
- document.archive for archival
- document.delete_physical for exceptional administrative deletion

A user must not access a file by guessing its storage path.

## 20. Document Storage Security

The browser must never receive raw server filesystem paths.

Storage keys are internal identifiers.

Download flow:

Request -> authenticate -> authorize document -> resolve storage key -> verify file/metadata -> stream -> audit if required

Never construct filesystem paths directly from untrusted request parameters.

Prevent path traversal, arbitrary file reads, symlink escape where applicable, MIME confusion, and cross-Project downloads.

## 21. Document Replacement and Deletion

Replacement:

- requires document.replace
- creates audit event
- new file becomes active
- old file becomes superseded/archived according to Document policy

Physical deletion:

- requires document.delete_physical
- Admin-only by default
- audited
- blocked where retention policy requires preservation

V1 normal deletion is archive + audit; physical deletion is exceptional.

## 22. Contract and Restriction Security

Contract actions inherit Project and Operation authorization.

Restriction evaluation is server-side.

Importing restrictions requires:

- restriction.import
- valid Project scope
- validated input
- import preview
- audit

Rule management requires restriction.manage_rules.

Override/unblock requires explicit privileged permission and reason.

No client-side restriction result is authoritative.

## 23. Appointment Security

Appointment authorization follows Project scope.

Examples:

- appointment.view
- appointment.create
- appointment.reserve
- appointment.present
- appointment.no_show
- appointment.cancel
- appointment.complete
- appointment.manage_slots
- appointment.manage_types
- appointment.manage_reminders

Capacity allocation must occur transactionally on the server.

## 24. Template and Print Security

Template permissions defined in FORMS_AND_PRINTING.md remain authoritative.

Template access does not automatically grant access to every Operation or Document used as preview data.

PDF generation re-authorizes:

- Operation
- template
- generated-document action
- source version

A template must never retrieve data the requesting user cannot access.

## 25. Backup and Restore Security

Backup access is privileged.

Recommended:

- backup.create for authorized administrative role
- backup.configure for high privilege
- backup.restore Admin-only by default

Restore requires:

1. authenticated privileged user
2. explicit confirmation
3. pre-restore backup
4. integrity validation
5. restore
6. post-restore validation
7. audit

Backup files contain sensitive information and must be protected like the database.

## 26. Audit Architecture

Audit is a security control.

Record at least:

- authentication events
- authorization-sensitive changes
- user/role changes
- Project-access changes
- Operation state changes
- finalization
- correction requests/approvals
- restriction imports/overrides
- document replacement/archive/physical deletion
- template activation
- generated document events where configured
- backup/restore
- security/settings changes

Each event should include:

- event ID
- timestamp
- actor user ID where available
- Project/context
- entity type
- entity ID
- action
- result
- reason/comment where required
- request/session correlation ID where available
- before/after summary for configuration changes where appropriate

Never store passwords, authentication secrets, or signing keys in audit.

## 27. Audit Immutability

Ordinary users cannot edit or delete audit events.

Audit is append-oriented.

If an audit correction is ever necessary, create a new audit event rather than silently changing history.

Physical deletion of audit data is exceptional, follows retention policy, and must itself be audited.

## 28. Configurable Audit Level

Recommended levels:

### Minimal

High-risk and security-sensitive actions.

### Standard

Business state changes plus high-risk actions.

### Detailed

Important field-level changes where practical.

Regardless of level, mandatory events include:

- login success/failure where policy requires
- permission/role changes
- Project-access changes
- finalization
- correction approval
- restriction override/unblock
- physical document deletion
- backup restore
- security configuration changes

Mandatory audit cannot be disabled by ordinary configuration.

## 29. Central Authorization Service

Recommended conceptual service:

authorize(user, action, resource, context)

Inputs:

- authenticated user
- permission/action
- resource
- Project
- Operation/Contract/Document context
- optional workflow state

Output:

- allowed/denied
- internal reason/code
- required permission if denied

Business services remain responsible for domain validation.

Do not scatter independent permission logic across templates, JavaScript, or random route handlers.

## 30. API Security

Every protected API endpoint must:

- authenticate
- authorize
- validate input
- enforce Project/entity scope
- use parameterized database operations
- avoid leaking internal errors
- apply request-size limits where relevant
- validate uploads
- avoid unsafe filesystem operations

Errors should distinguish unauthenticated, unauthorized, invalid request, and not-found where safe.

When resource existence itself is sensitive, unauthorized requests may return a generic not-found response.

## 31. Input and File Security

All user-controlled input is untrusted.

Validate:

- strings and lengths
- IDs
- dates
- enums
- numeric ranges
- filenames
- MIME types
- file sizes
- template definitions
- QR configuration
- import files

Uploaded files must:

- receive generated internal names
- not rely on extension alone
- be type/content validated as practical
- have size limits
- live outside executable application directories
- never be executed

## 32. Secret Management

Potential secrets:

- password-hashing configuration
- session secrets
- QR signing keys
- future external-service credentials

Rules:

- never in source code
- never in templates
- never returned to frontend
- never in logs/audit
- protected during backup

Exact V1 local secret storage is an implementation decision.

## 33. SQLite Security

SQLite is server-side only.

Requirements:

- foreign keys enabled on every connection
- WAL recommended
- busy timeout configured
- transactions for sensitive multi-step operations
- filesystem permissions restrict DB access
- clients never mount/open DB directly
- backup/restore uses a safe SQLite-aware mechanism

Architecture remains migration-friendly toward PostgreSQL.

## 34. Concurrency and Security

Authorization must be evaluated against current resource state inside the transaction where race conditions matter.

Examples:

- finalization
- numbering
- appointment capacity
- correction approval
- restore
- permission changes

Optimistic locking prevents stale clients from silently overwriting current data.

Security decisions must never rely solely on state previously loaded by the browser.

## 35. Separation of Duties

Default posture should prevent one low-privilege user from completing an entire high-risk workflow alone.

Recommended:

- creator cannot approve own correction
- restriction override requires elevated permission
- role assignment requires elevated permission
- backup restore is Admin-only
- physical document deletion is Admin-only
- security configuration requires privileged role

Exceptions must be explicit and audited.

## 36. Admin Safety

Admin is powerful but remains auditable.

At minimum audit:

- user creation/disable
- role creation/edit
- role assignment
- Project-access changes
- permission/security configuration
- physical document deletion
- backup restore
- security setting changes

Avoid hidden superuser bypasses that cannot be audited.

## 37. Project Access Changes

Changing Project membership is sensitive.

Flow:

1. authorize access management
2. identify target user
3. identify Project
4. select access/scope
5. validate actor privileges
6. apply transaction
7. invalidate affected sessions/cache if required
8. audit before/after access state

Revoked Project access should take effect promptly.

## 38. User Disable

Disabling a user should:

- prevent new login
- invalidate active sessions where supported
- preserve historical audit attribution
- preserve ownership metadata
- prevent new protected actions

Do not delete historical records because a user was disabled.

## 39. Search Security

Global search is a common data-leak vector.

Every search query must apply authorization filters before returning results.

This includes:

- Operation
- Contract
- Person
- Property
- Appointment
- Document
- registration number
- contract number

Never query everything and filter only in the UI.

## 40. Logging vs Audit

Application logs and business audit are different.

### Logs

For diagnostics:

- exceptions
- performance
- infrastructure state
- renderer errors
- database errors

### Audit

For accountability:

- who changed what
- who finalized
- who approved
- who overrode
- who accessed sensitive configuration
- who restored

Logs may rotate. Audit follows retention policy.

Neither should contain passwords or secrets.

## 41. V1 Security Baseline

V1 must provide:

- authenticated users
- secure password hashes
- configurable roles
- configurable permissions
- Project membership/access
- server-side authorization
- document authorization
- immutable finalized records
- correction approval workflow
- privileged overrides
- audit
- optimistic locking
- protected filesystem storage
- safe upload handling
- protected backup/restore
- no direct client access to SQLite
- no arbitrary template execution

## 42. Recommended Initial Roles

### Administrator

Broad system, Project, and security privileges, including restore and role management.

### Project Manager

Project administration and business workflow management without unrestricted system-security privileges.

### Operator

Day-to-day appointments, people, properties, operations, documents, and permitted printing.

### Reviewer

Review, validation, and approval responsibilities without broad configuration privileges.

### Read Only

Authorized viewing/search/printing without modification.

These are seed roles, not immutable roles.

## 43. Acceptance Criteria

The subsystem is acceptable for V1 when:

- every protected API requires authentication
- permissions are centrally defined
- roles can be configured
- users can have multiple roles
- Project access is independently managed
- project-scoped permissions require Project membership
- shared Person/Property records do not leak across Projects
- Operation authorization checks Project, permission, state, and business rules
- finalized records cannot be normally edited
- correction approval is separately authorized
- overrides require explicit permission and reason
- documents cannot be accessed by guessed path or ID
- search applies authorization filters
- role/Project-access changes are audited
- audit records cannot be edited by normal users
- Admin actions remain auditable
- optimistic locking prevents silent overwrites
- restore is privileged and audited
- secrets never appear in templates, frontend data, logs, or audit
- uploaded files are validated and stored safely
- SQLite remains server-side only

## 44. Open Decisions

1. Exact authentication/session mechanism.
2. Password policy and account lockout policy.
3. Exact global/project permission catalog.
4. Whether a user may have different roles per Project.
5. Whether a single role can contain both global and project-scoped permissions.
6. Exact Project-access levels if more than membership is needed.
7. Re-authentication requirements for critical actions.
8. Audit retention and archival strategy.
9. Exact secret storage mechanism for local Windows deployment.
10. Whether MFA is V1 or future.
11. Whether Admin may approve their own correction in exceptional deployments.
12. Exact authorization caching strategy.
13. Exact API rate/request-size limits for LAN deployment.

These decisions must not weaken the deny-by-default, Project-scoped, server-side authorization model.
