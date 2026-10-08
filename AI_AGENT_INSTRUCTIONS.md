# AI_AGENT_INSTRUCTIONS.md

## 1. Purpose

This document is the execution contract for AI coding agents working on SABT.

An agent must treat the repository architecture documents as authoritative project requirements.

The agent is not allowed to invent a competing architecture merely because another approach is technically possible.

The primary goal is to implement the agreed system safely, incrementally, testably, and without violating established domain rules.

---

## 2. Required Reading Order

Before making a non-trivial code change, the agent must read the relevant repository documents.

Minimum architecture context:

1. README.md
2. ARCHITECTURE.md
3. DOMAIN_MODEL.md
4. WORKFLOWS.md
5. DATABASE_SCHEMA.md
6. ERD.md
7. UI_FLOW.md
8. APPOINTMENTS_AND_REMINDERS.md
9. FORMS_AND_PRINTING.md
10. SECURITY_AND_ROLES.md
11. BACKUP_AND_RESTORE.md
12. OPEN_DECISIONS.md

For a focused task, the agent must at least read every document directly related to that task.

When documents conflict, do not silently choose one. Identify the conflict and resolve it against the most recent explicit project decision or ask for clarification when necessary.

---

## 3. Source of Truth Hierarchy

Use this hierarchy:

1. Explicit user decisions in the project conversation
2. Explicit architectural decisions recorded in repository documents
3. Domain/workflow invariants in repository documents
4. Existing tests and accepted behavior
5. Existing implementation details
6. Agent assumptions

Agent assumptions are the weakest source.

Do not use existing code to justify violating an explicit architecture decision.

If implementation and specification disagree, report the discrepancy and normally align implementation with the specification.

---

## 4. Product Boundary

SABT is a case/document management system for real-estate transfer and registration workflows.

It is not:

- a public real-estate marketplace
- an advertising portal
- a general CRM
- an accounting system
- a payment processor
- a banking integration
- an official government registry replacement

Financial transactions happen outside SABT.

SABT may store transaction/payment/commission receipts as documents attached to the relevant business operation.

Do not add financial transaction processing unless explicitly requested later.

---

## 5. Technology Baseline

V1 technology baseline:

- Python
- FastAPI
- SQLAlchemy
- Alembic
- SQLite
- server-side HTTP API
- lightweight HTML/Jinja or equivalent frontend
- CSS
- vanilla JavaScript unless a later explicit decision changes this
- filesystem for managed files
- PDF generation for printable documents

Clients must never open SQLite directly.

The server is the database boundary.

SQLite must be configured safely, including foreign keys and an appropriate concurrency strategy.

The architecture should remain migration-friendly toward PostgreSQL.

Do not introduce a large framework or infrastructure stack without a concrete requirement.

---

## 6. Deployment Baseline

V1 is local/Windows/LAN oriented.

Expected topology:

Client browser
-> HTTP
-> FastAPI server
-> SQLAlchemy
-> SQLite

Managed files are stored on the server filesystem.

A Windows installer may be introduced later.

Do not prematurely optimize the project around cloud-native deployment.

---

## 7. Domain Invariants

The following are non-negotiable unless explicitly changed by the user.

### Projects

- Multiple projects are supported.
- People are centrally reusable across projects.
- Properties are centrally reusable across projects.
- Project-specific configuration must not duplicate master identity unnecessarily.

### Person

Use a central Person entity plus operation snapshots.

A finalized historical operation must retain its own immutable person snapshot.

Changes to a Person after finalization must not rewrite historical finalized data.

### Property

Use a central Property entity plus operation snapshots.

A finalized historical operation must retain its own immutable property snapshot.

Changes to a Property after finalization must not rewrite historical finalized data.

### Appointment

Appointment and Operation are independent entities.

An Appointment may exist without an Operation.

An Operation may exist without an Appointment.

One Appointment may lead to multiple Operations.

Appointment Type controls Present behavior.

### Operation

Operation is the central business-process entity.

Operation Types may be global base definitions with project-specific activation/configuration.

Operation Types may define:

- fields
- required documents
- workflow
- print templates
- appointment behavior
- numbering behavior
- other capabilities

Core operation fields are fixed; custom fields extend the model.

### Contract

An Operation may have zero or one Contract.

Each Contract has exactly one Property.

Contract Number is manually entered.

Contract Number is a business key, not the database primary key.

Contract-number uniqueness is configurable by Admin.

Registration Number is generated according to configurable policy.

### Parties

An Operation may have multiple parties.

Party roles are dynamic/admin-defined.

Do not hard-code a fixed list of party roles into the core domain model.

### Finalization

A normal finalized operation is immutable.

Correction is performed through a Correction Request, approval, and new version.

Do not silently mutate finalized records.

### Documents

Documents are first-class entities.

Actual files are stored on the filesystem.

Metadata is stored in the database.

Document replacement supersedes the previous file.

V1 does not require physical file-version history, but replacement must be audited.

Archive is preferred over ordinary deletion.

Physical deletion is Admin-only.

### Restrictions

V1 restriction/blacklist behavior is Contract-oriented.

Import supports:

- CSV
- Excel
- clipboard/paste

Restriction behavior is rule-based and may warn or block according to configured rules.

Overrides require appropriate permission and audit.

### Numbering

Registration numbering is configurable.

The system must support configurable:

- format
- scope
- prefix
- sequence
- reset policy
- collision handling

Number allocation must be safe under concurrent users.

### Custom Fields

Custom fields are metadata-driven.

They may apply to supported entities.

Do not create ad-hoc database columns for every future custom field requirement unless explicitly justified.

---

## 8. Snapshot Rules

Snapshot behavior is central to historical integrity.

At Operation creation:

- create a working snapshot.

At Finalize:

- create immutable final snapshots.

Historical finalized operations use their own snapshots.

Do not rebuild historical truth from mutable master records.

Where practical, use both structured immutable snapshot data and canonical immutable JSON to support reproducibility.

---

## 9. Workflow Rules

Base Operation lifecycle:

Draft
-> In Progress
-> Ready for Finalization
-> Finalized

Operation Type may configure workflow details while remaining compatible with the base state model.

Finalization must validate at minimum:

- required fields
- required parties
- required documents
- workflow state
- restrictions
- numbering requirements
- concurrency/version state

Do not allow the frontend alone to decide whether finalization is legal.

The backend is authoritative.

---

## 10. Correction Rules

Correction of finalized data is not ordinary editing.

Required conceptual flow:

Finalized
-> Correction Request
-> Approval
-> New Version
-> Finalization

Every correction must preserve historical auditability.

Do not overwrite finalized truth without creating the required correction/version history.

---

## 11. Appointment Rules

Appointment states include:

- Reserved
- Present
- No-Show
- Cancelled
- Done

Free is a calculated slot state rather than necessarily a persisted appointment row.

Present behavior is configurable by Appointment Type:

- attendance only
- attendance + start operation

Capacity and conflict checking are backend responsibilities.

Concurrent reservation requests must not allocate the same capacity unit twice.

---

## 12. Reminder Rules

Reminder Engine is rule-based.

Rules may be scoped to:

- Project
- Appointment Type
- future supported scopes

Triggers may include:

- shift start
- previous workday end
- before appointment
- reservation
- state change
- Present
- No-Show
- Cancel
- operation deadline

V1 delivery is primarily in-app.

The architecture should remain extensible for future SMS/email/WhatsApp/calendar integrations.

Deduplication must be backend-enforced.

---

## 13. UI Rules

The primary UI is Persian and RTL.

The architecture must be i18n-ready.

Technical values may automatically use LTR direction where appropriate, such as:

- contract numbers
- registration numbers
- identifiers
- filenames
- URLs
- codes

Operation UI uses:

- stepper
- quick navigation
- review/finalization stage

Dashboard includes:

- Today
- Calendar
- Quick Search
- Recent Operations
- Quick Actions

Do not duplicate authorization logic in frontend code.

Frontend visibility is UX only; backend authorization remains mandatory.

---

## 14. Form and Printing Rules

Form Designer requirements:

- drag/drop
- precise X/Y/W/H
- user-facing millimeters
- internal PDF points

V1 should support A4 portrait and landscape.

Template revisions are immutable after activation.

Generated PDFs must reference the exact template revision used.

Preview and final generation should use the same backend rendering engine.

Do not allow arbitrary executable code inside templates.

Dynamic bindings must come from an approved field-binding system.

Missing required fonts/assets must be detected during template validation/activation.

---

## 15. QR Rules

QR content is server-generated.

V1 QR payload supports:

- dynamic payload
- checksum and/or signature
- configurable template position
- configurable size

No public verification URL is required in V1.

Do not place sensitive secrets directly in QR payloads.

The architecture should permit future public verification.

---

## 16. Security Rules

Backend is the authoritative security boundary.

Use:

- authentication
- secure password hashing
- server-side sessions/authentication state
- configurable roles
- configurable permissions
- deny-by-default authorization
- project-scoped authorization where required
- document/entity authorization
- audit for sensitive actions

Use a centralized authorization concept such as:

authorize(user, action, resource, context)

Do not scatter incompatible permission checks throughout unrelated modules.

Search endpoints must enforce authorization.

Never trust a project ID, operation ID, document ID, or other resource ID supplied by the client without authorization checks.

---

## 17. Roles

Initial conceptual roles:

- Administrator
- Project Manager
- Operator
- Reviewer
- Read Only

Roles and permissions remain configurable.

Do not hard-code role names into business logic when a permission-based check is sufficient.

Prefer permissions such as:

operation.create
operation.edit
operation.finalize
operation.correct
document.view
document.replace
backup.create
backup.restore

over checks such as:

if user.role == "Administrator"

except where a truly global administrative operation requires it.

---

## 18. Concurrency

Two or more users may work simultaneously.

Use:

- optimistic locking/version counters for normal edits
- short-lived application locks for sensitive forms
- transactional allocation for capacity and numbering
- no silent overwrite

The backend must detect stale updates.

The user must receive a clear conflict response rather than having one user's changes silently replace another user's changes.

---

## 19. Audit

Audit level is configurable, but sensitive actions are always audited.

Mandatory audit candidates include:

- login/security events
- finalization
- correction requests/approvals
- restriction overrides
- document replacement/deletion
- numbering changes
- role/permission changes
- backup/restore
- template activation
- important configuration changes

Audit data should be append-oriented.

Never log passwords, secret keys, or sensitive credentials.

---

## 20. Backup and Restore

Backup is a full restorable snapshot.

It includes:

- SQLite database
- managed documents
- generated PDFs
- templates
- branding
- required application-managed files

V1 supports:

- manual backup
- automatic backup
- rotation
- full restore

Restore is Admin-only.

Pre-restore backup is mandatory.

Backup must include a manifest and integrity hashes.

Restore must:

- validate archive first
- check application/schema compatibility
- prevent path traversal
- block concurrent writes
- restore safely
- validate after restoration
- audit the result

Do not implement backup as "copy the SQLite file and call it done."

---

## 21. Storage Rules

Recommended logical storage:

storage/
- documents/
- generated/
- templates/
- branding/
- temp/

Database:

data/sabt.db

Backups:

backups/

Never expose raw filesystem paths to clients.

Store logical storage keys in database metadata.

Resolve physical paths only inside controlled server-side storage services.

---

## 22. Database Rules

Use SQLAlchemy models and Alembic migrations.

Foreign keys must be enabled.

Multi-step business operations must use transactions.

Do not make business numbers database primary keys.

Do not assume a business number is globally unique unless the configured policy says so.

Prefer stable internal identifiers.

UUIDs are preferred if they improve future synchronization/migration, but the final identifier strategy must be applied consistently.

Avoid circular relationships where one side can own the relationship cleanly.

Example:

Contract owns optional Operation relationship through contracts.operation_id with a uniqueness constraint.

Do not unnecessarily store both operations.contract_id and contracts.operation_id.

---

## 23. Schema Change Rules

Every schema change requires an Alembic migration.

Do not edit production schema manually as part of normal application behavior.

Migrations must be:

- deterministic
- reviewable
- reversible where practical
- tested against representative data

Never silently drop user data.

Destructive migrations require explicit review.

---

## 24. API Design Rules

API endpoints should represent domain actions, not just database CRUD.

Examples:

- finalize operation
- request correction
- approve correction
- mark appointment present
- reserve appointment
- import restrictions
- replace document
- generate PDF
- create backup
- restore backup

A domain action must validate authorization, workflow, business rules, and concurrency on the server.

Do not expose raw SQLAlchemy model mutation as a substitute for business services.

---

## 25. Service-Layer Rules

Keep domain/business rules out of:

- Jinja templates
- browser JavaScript
- raw route handlers
- database models when the rule requires orchestration

Prefer layers such as:

- API/router
- authorization
- application/service
- domain rules
- persistence/repository
- storage service
- rendering/PDF service
- scheduler/background jobs

The project should remain lightweight; do not create abstractions solely for theoretical purity.

Introduce a layer when it has a concrete responsibility.

---

## 26. File Storage Service

All managed-file operations should pass through a controlled storage service.

Responsibilities:

- generate safe storage keys
- resolve storage paths
- prevent path traversal
- save files
- calculate hashes
- retrieve files
- replace files
- archive files
- delete physically only when authorized
- validate MIME/size
- coordinate metadata

Business code should not freely concatenate filesystem paths.

---

## 27. Document Upload Rules

Validate:

- size
- MIME/type
- extension where applicable
- storage key
- authorization
- target entity authorization

Never trust the client-provided filename as a storage path.

Use generated internal names/keys.

Preserve original filename only as metadata if needed.

---

## 28. Import Rules

CSV/Excel/clipboard imports must use a staged workflow:

1. upload/paste
2. parse
3. map fields
4. validate
5. preview
6. confirm
7. commit transactionally
8. record import batch
9. audit

Do not partially mutate production data during the preview stage.

Large imports should be bounded and monitored.

---

## 29. Search Rules

Search must be backend-authorized.

Possible search targets:

- Operation
- Contract
- Person
- Property
- Appointment
- Document

Search results must never reveal records from projects/resources the user cannot access.

Technical fields such as identifiers and numbers should support appropriate exact/prefix matching.

Ranking and advanced search remain configurable/open design areas.

---

## 30. Form Binding Rules

Templates may reference approved data bindings only.

A binding must declare:

- source entity
- field
- data type
- formatting behavior
- authorization sensitivity if needed

Do not allow a template author to execute arbitrary Python, JavaScript, SQL, or filesystem commands.

---

## 31. PDF Rules

PDF generation must be deterministic as far as practical.

Generated PDF metadata should include:

- operation/reference
- template revision
- generation timestamp
- file hash

Historical documents must be reproducible from immutable operation version/snapshot plus exact template revision where required.

---

## 32. Localization Rules

Internal database timestamps should use a consistent Gregorian representation.

User-facing date/calendar presentation is Persian/Jalali.

Do not store formatted Jalali strings as the only source of truth for timestamps.

Timezone policy remains an open design decision and must be explicit before time-sensitive scheduling is finalized.

---

## 33. Error Handling

Errors must be:

- safe
- actionable
- structured
- auditable where appropriate

Do not expose:

- SQL statements
- filesystem internals
- stack traces
- secrets
- internal credentials

to ordinary users.

Use stable application error codes for important business failures.

---

## 34. Logging

Logs are operational diagnostics, not a replacement for audit.

Do not log:

- passwords
- tokens
- private signing keys
- full sensitive documents
- unnecessary personal data

Correlate important requests/actions with safe request IDs where practical.

---

## 35. Testing Requirements

A meaningful feature is incomplete without tests.

At minimum, add tests appropriate to the change:

### Unit tests

For:

- domain rules
- validation
- numbering
- restriction evaluation
- permission logic
- snapshot generation

### Integration tests

For:

- database transactions
- API authorization
- workflows
- file storage
- document operations
- backup/restore

### Concurrency tests

For:

- appointment capacity
- numbering
- optimistic locking
- sensitive operations

### Regression tests

Every discovered production-class bug should become a regression test where practical.

---

## 36. Testing Domain Invariants

Tests must explicitly protect high-value invariants, including:

- finalized operation is immutable through ordinary edit
- correction creates a new version
- historical snapshot survives Person changes
- historical snapshot survives Property changes
- one Operation has at most one Contract
- one Contract has exactly one Property
- one Appointment may link to multiple Operations
- Operation may exist without Appointment
- Contract Number follows configured uniqueness
- Registration Number follows configured numbering policy
- unauthorized project data is not searchable
- unauthorized documents cannot be downloaded
- concurrent appointment capacity cannot be oversold
- concurrent numbering cannot collide
- invalid backup cannot be restored

---

## 37. Implementation Order

Do not build the entire system in one large change.

Recommended sequence:

### Phase 1: Foundation

- repository structure
- FastAPI application
- configuration
- database connection
- SQLAlchemy
- Alembic
- health endpoint
- basic error handling
- test infrastructure

### Phase 2: Security Foundation

- users
- roles
- permissions
- authentication
- sessions
- authorization service
- audit foundation

### Phase 3: Core Master Data

- Project
- Person
- Property
- project access

### Phase 4: Operations

- Operation Type
- project activation
- Operation
- Operation Party
- snapshots
- workflow
- finalization
- versioning/correction

### Phase 5: Contract

- Contract
- property relationship
- contract number
- registration numbering
- restrictions

### Phase 6: Documents

- document types
- storage service
- upload/replace/archive
- authorization
- audit

### Phase 7: Appointments

- Appointment Type
- slots
- calendar
- reservation
- Present
- No-Show
- Cancelled
- Done
- appointment-operation links

### Phase 8: Reminders

- rules
- scheduling
- in-app notifications
- deduplication

### Phase 9: Forms and PDF

- template model
- revisions
- designer data model
- renderer
- PDF
- QR
- branding

### Phase 10: Backup/Restore

- backup manifest
- snapshot
- archive
- validation
- rotation
- restore
- recovery

### Phase 11: UI Refinement

- dashboard
- operation stepper
- search
- responsive behavior
- accessibility
- Persian/RTL polish

The order may change when a concrete dependency requires it, but changes must be deliberate.

---

## 38. Vertical-Slice Development

Prefer vertical slices over creating every database table before any working behavior exists.

A vertical slice should include, as appropriate:

- model
- migration
- service
- API
- authorization
- UI
- tests
- audit
- documentation

Do not leave large undocumented half-built subsystems.

---

## 39. Definition of Done

A feature is not done merely because the endpoint works.

Definition of Done should normally include:

- domain rule implemented
- authorization enforced
- database migration added
- validation implemented
- audit added when required
- UI behavior implemented when applicable
- error states handled
- tests added
- documentation updated if architecture changes
- no known security regression
- no silent data loss

---

## 40. Working With Existing Code

Before changing an existing subsystem:

1. inspect current implementation
2. inspect relevant tests
3. inspect migration history
4. identify dependencies
5. identify architecture/spec mismatches
6. make the smallest coherent change

Do not rewrite unrelated code merely for style.

Avoid broad refactors while implementing an unrelated feature.

---

## 41. Refactoring Rules

Refactor when it improves:

- correctness
- security
- maintainability
- testability
- clear domain ownership

Do not refactor only because another architecture is fashionable.

Keep changes reviewable.

If a refactor is large, split it into safe stages.

---

## 42. Dependency Rules

Prefer Python standard library and already-approved dependencies when they satisfy requirements.

Before adding a new dependency, consider:

- necessity
- maintenance status
- security
- licensing
- Windows compatibility
- package size
- installation complexity
- whether the project can remain lightweight

Do not add a dependency for a trivial helper that can be safely implemented without it.

---

## 43. External Services

V1 does not require:

- payment gateway
- banking API
- SMS provider
- email provider
- WhatsApp
- public booking portal
- external calendar synchronization

If an external service becomes necessary, isolate it behind an adapter/service boundary.

Never make core domain logic dependent on a specific provider.

---

## 44. Background Jobs

Background jobs are appropriate for:

- automatic backups
- reminder scheduling
- heavy PDF generation when needed
- cleanup/maintenance

Jobs must be:

- idempotent where practical
- auditable
- concurrency-safe
- restart-safe
- bounded in retries

A job must not silently corrupt business state after process restart.

---

## 45. Transaction Rules

Use database transactions for multi-step business operations such as:

- finalization
- numbering allocation
- appointment capacity allocation
- correction approval/version creation
- restriction import commit
- permission changes
- backup metadata publication where relevant

Do not assume multiple SQL statements are atomic unless enclosed in the correct transaction.

---

## 46. Finalization Transaction

Finalization should behave as one controlled business transaction where practical.

Conceptually:

1. lock/check operation version
2. validate workflow
3. validate required fields
4. validate parties
5. validate documents
6. evaluate restrictions
7. allocate registration number if required
8. create immutable final snapshot/version
9. mark operation finalized
10. create required audit events
11. commit

If a required step fails, the operation must not become partially finalized.

---

## 47. Numbering Concurrency

Registration number allocation must be concurrency-safe.

Never implement numbering as:

read current number
-> increment in application memory
-> save

without a transaction/locking strategy.

The selected mechanism must prevent duplicate allocation under concurrent requests.

---

## 48. Authorization Context

Authorization may depend on:

- user
- global permissions
- project membership/access
- role
- target entity
- operation state
- action
- sensitive-data classification

Therefore a permission check may require resource context.

Do not reduce every authorization question to a simple role-name comparison.

---

## 49. Sensitive Operations

Sensitive operations should require explicit permission and often confirmation.

Examples:

- finalize
- correct finalized operation
- restriction override
- physical document deletion
- role/permission changes
- restore
- backup deletion
- numbering-policy changes
- template activation

The UI should make these actions visibly distinct.

---

## 50. Data Deletion

Business records should generally be archived rather than deleted.

Physical deletion is exceptional.

For any deletion feature, determine:

- whether business history requires retention
- whether audit must remain
- whether documents are referenced
- whether foreign-key relationships permit deletion
- whether the action is reversible

Never implement cascade deletion casually.

---

## 51. Project Isolation

Because Person and Property are centrally shared:

- project access controls must be explicit
- shared master data must not expose unauthorized project context
- operations/documents/appointments remain project-scoped where defined
- search must filter according to authorization
- project-specific configuration must be isolated

A user seeing a Person record must not automatically gain access to every operation or document associated with that person.

---

## 52. Performance Principles

V1 should optimize for correctness first.

Avoid premature optimization.

Still protect against obvious issues:

- N+1 queries in important list views
- unbounded document queries
- loading entire files into memory unnecessarily
- unbounded imports
- expensive PDF generation inside ordinary request paths when asynchronous processing is justified

Use pagination for potentially large collections.

---

## 53. UI Performance

The UI should remain lightweight.

Prefer:

- server-rendered pages where appropriate
- small focused JavaScript modules
- progressive enhancement
- predictable forms
- pagination/filtering

Do not turn the project into a large SPA without an explicit requirement.

---

## 54. Accessibility

At minimum:

- keyboard-accessible controls
- labels for form fields
- visible focus
- meaningful error messages
- status information not conveyed by color alone
- adequate contrast
- logical RTL reading order

Sensitive confirmations should be keyboard accessible.

---

## 55. Internationalization

Do not scatter Persian strings throughout core business logic.

Use a translation-ready structure.

The initial language is Persian.

Future languages should be possible without rewriting domain services.

---

## 56. Technical Directionality

Support automatic direction for mixed content.

Examples:

RTL:

- labels
- Persian descriptions
- normal narrative text

LTR:

- URLs
- file paths
- technical IDs
- many codes
- hashes

Do not force all content into one direction.

---

## 57. Documentation Rules

If a change modifies architecture, domain behavior, schema, security, workflow, or an important invariant:

- update the relevant MD document
- update OPEN_DECISIONS.md when a decision becomes resolved
- update ERD/schema documentation when relationships change
- update acceptance criteria where appropriate

Documentation drift is a defect.

---

## 58. Decision Discipline

When an implementation choice is not specified:

1. check OPEN_DECISIONS.md
2. check related architecture documents
3. check existing tests/implementation
4. identify whether the choice affects domain behavior or only implementation detail

If it affects domain behavior and is unresolved, do not silently invent a business rule.

Record the decision or ask the user.

---

## 59. No Silent Scope Expansion

Do not add:

- accounting
- payment processing
- public marketplace
- external registry integration
- messaging providers
- cloud deployment
- advanced analytics
- unrelated CRM capabilities

unless explicitly requested.

A technically interesting feature is not automatically a project requirement.

---

## 60. Agent Change Discipline

Every implementation task should produce:

- concise change summary
- files changed
- migrations, if any
- tests added/updated
- unresolved decisions
- known limitations

For larger changes, report:

- architectural impact
- security impact
- data migration impact
- rollback considerations

Do not claim completion without actually running the relevant tests/checks.

---

## 61. Required Agent Behavior Before Coding

Before starting a substantial task, the agent should answer internally:

1. What domain rule am I implementing?
2. Which document defines it?
3. Which entities are involved?
4. What permissions are required?
5. What workflow/state transitions are involved?
6. Does it change finalized/historical data?
7. Does it require a transaction?
8. Does it require audit?
9. Does it require migration?
10. What concurrency risk exists?
11. What tests prove correctness?
12. Does the change modify an architectural decision?

If any critical answer is unknown, inspect the repository or ask for clarification instead of guessing.

---

## 62. Required Agent Behavior After Coding

After implementation:

1. run formatting/linting tools available in the repository
2. run targeted tests
3. run relevant integration tests
4. run broader tests when practical
5. inspect migration status
6. inspect changed files
7. verify no secrets were introduced
8. verify documentation consistency
9. report failures honestly

Never state "all tests pass" without actually running them.

---

## 63. Commit Discipline

Prefer focused commits.

Good examples:

- feat: add operation finalization workflow
- fix: prevent appointment capacity race
- docs: define backup restore architecture
- test: cover contract number uniqueness

Avoid giant commits mixing unrelated features.

A documentation-only architectural decision should be isolated when practical.

---

## 64. Security Review Trigger

Perform an explicit security review when changing:

- authentication
- authorization
- file upload/download
- permissions
- audit
- QR signing
- backup/restore
- imports
- template rendering
- SQL/query construction
- external integrations

At minimum check:

- privilege escalation
- data leakage
- path traversal
- injection
- insecure direct object reference
- race conditions
- unsafe deserialization
- secret exposure

---

## 65. Data Migration Trigger

Any change that modifies:

- column semantics
- relationship cardinality
- numbering
- snapshots
- finalized records
- document metadata
- permissions
- stored custom-field types

must consider existing data.

Do not assume a clean database.

Migrations should be tested with representative existing data.

---

## 66. Final Agent Contract

The coding agent must preserve these fundamental properties:

- backend is authoritative
- domain rules are explicit
- finalized history is immutable
- corrections create versions
- snapshots preserve historical truth
- permissions are enforced server-side
- project isolation is enforced
- documents are controlled through a storage service
- SQLite is never directly exposed to clients
- multi-step business actions are transactional
- concurrent users cannot silently overwrite each other
- sensitive actions are audited
- backups are full and restorable
- restore is Admin-only and protected by pre-restore backup
- templates cannot execute arbitrary code
- no silent data loss
- no silent scope expansion

When in doubt, prefer preserving historical integrity, security, authorization, and explicit business rules over convenience.
