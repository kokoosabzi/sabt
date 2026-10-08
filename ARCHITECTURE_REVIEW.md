# SABT — Pre-Implementation Architecture Review

Version: 0.1
Status: Pre-Implementation Gate

## Purpose

This document records the architecture review performed after the initial specification set was created.

The goal is not to redesign SABT. The goal is to identify contradictions, underspecified boundaries, and decisions that must be frozen before implementation begins.

No application code should be generated for a domain area that still has an unresolved business-semantic conflict.

## 1. Overall Assessment

The architecture is coherent enough to begin foundation work, but the domain/schema boundary is not yet safe enough to freeze the complete database schema.

The strongest parts are:
- Operation-centered workflow
- independent Appointment and Operation
- immutable finalized history
- Person/Property master records plus snapshots
- configurable Operation Types
- dynamic Party Roles
- server-side authorization
- filesystem document storage with DB metadata
- transactional business actions
- full backup/restore concept
- template-driven PDF generation
- explicit AI coding-agent contract

The main remaining risk is semantic precision around ownership, scope, snapshots, configuration inheritance, and versioning.

## 2. Critical Finding: Shared Person/Property vs Project Scope

Person and Property are described as reusable master entities, while project decisions state that they are centrally reusable across Projects.

The current Property model contains project_id, which implies a Property belongs to one Project. This conflicts with the central reusable-master concept.

Recommended direction: Property should be a central master record. Project-specific association/configuration should be represented separately where required. The same conceptual separation should be considered for Person if future project-specific attributes are required.

Do not solve cross-project sharing by duplicating the Person/Property master record.

Status: MUST RESOLVE BEFORE FINAL SCHEMA FREEZE.

## 3. Critical Finding: Operation Property Context

Operation has a Property context, Contract has exactly one Property, and Operation may exist before a Contract.

Recommended direction: Operation.property_id represents the working/current selected property for the operation. Contract.property_id represents the legally relevant property relationship once a Contract exists.

Finalized snapshots must preserve the property state used by the finalized business version.

Status: CLARIFY BEFORE OPERATION/CONTRACT PERSISTENCE.

## 4. Critical Finding: Contract Relationship Ownership

Use Contract.operation_id as the authoritative 0..1 relationship, with a unique constraint on Contract.operation_id.

Do not maintain both Operation.contract_id and Contract.operation_id for the same relationship.

Status: RESOLVED ARCHITECTURAL DIRECTION.

## 5. Critical Finding: Snapshot Timing and Scope

Working snapshots are captured at Operation creation. Immutable final snapshots are created at Finalize. Correction creates a new version and new final snapshot state.

Recommended rule: OperationVersion.snapshot_json is the canonical immutable business snapshot for a finalized version. Structured Person/Property snapshot tables may exist for queryability, but the system must not maintain two independent sources of historical truth.

Status: MUST BE EXPLICIT BEFORE IMPLEMENTATION.

## 6. Critical Finding: Operation Version vs Document Version

OperationVersion represents a finalized business state. Document replacement changes the current file represented by a Document entity.

Do not use OperationVersion to imply that every attached document has a historical binary version.

If reproducibility of a finalized PDF requires historical source documents, the architecture must explicitly define which documents are included in the immutable business snapshot or version manifest.

Status: REQUIRES CLARIFICATION.

## 7. Critical Finding: Operation Type Configuration

Operation Types can define fields, custom fields, required documents, workflow, print templates, appointment behavior, numbering, and validation.

Project-specific activation/configuration is also required.

Every configurable property needs an explicit inheritance rule: global only, project override allowed, project required, immutable after activation, or versioned after activation.

Do not put critical business configuration into an unstructured config_json. Configuration affecting authorization, workflow, numbering, required documents, or other critical behavior should use dedicated relational structures.

Status: MUST DEFINE OVERRIDE MATRIX BEFORE SCHEMA FREEZE.

## 8. Critical Finding: Custom Field Scope

Custom fields may apply to Person, Property, Operation, Contract, Appointment, and other supported entities.

Field definitions can be global, project-scoped, or Operation-Type-scoped. Scope and inheritance precedence must be explicit.

Status: REQUIRES EXPLICIT SCOPE PRECEDENCE.

## 9. Critical Finding: Party Role Governance

Roles are dynamic and duplicate assignments are allowed.

Unresolved questions include mandatory roles, whether one Person can occupy multiple roles, whether duplicate same-role assignments are valid, whether sequence has semantic meaning, and whether roles are project-specific.

Recommended baseline: allow multiple assignments, let Operation Type define required roles/cardinality, and retire used roles instead of deleting them.

Status: REQUIRED BEFORE WORKFLOW VALIDATION.

## 10. Critical Finding: Registration Number Allocation

Define scope, prefix, sequence width, reset period, next-value storage, gap policy, allocation timing, rollback behavior, and concurrency mechanism.

Recommended direction: allocate only at successful Finalization when required. Use dedicated numbering configuration/state and a transaction-safe allocation mechanism. Never use MAX(registration_number) + 1.

Status: MUST RESOLVE BEFORE CONTRACT FINALIZATION.

## 11. Critical Finding: Contract Number Uniqueness

Contract Number is manually entered and uniqueness is configurable.

Represent uniqueness policy explicitly, such as global, project, operation-type, or no uniqueness. Enforce the configured policy transactionally.

Status: MUST RESOLVE BEFORE CONTRACT IMPLEMENTATION.

## 12. Critical Finding: Timezone

Timezone affects appointments, reminders, shift boundaries, backup scheduling, audit display, and numbering resets.

Recommended direction: store timezone-aware UTC instants internally where practical and define project/user presentation timezone explicitly. Do not use server-local timezone as an implicit business rule.

Status: MUST RESOLVE BEFORE SCHEDULING.

## 13. Critical Finding: Backup Encryption and Secrets

Backup architecture defines full restorable snapshots and integrity hashes, but encryption, key ownership, secret inclusion, and cross-machine restore behavior remain open.

Do not place application secrets or private signing keys into ordinary backup archives in plaintext. Define secret recovery separately from business-data restore.

Status: MUST RESOLVE BEFORE PRODUCTION BACKUP.

## 14. Critical Finding: Template Revisioning

Active template revisions must be immutable. Editing creates a new revision. Generated documents retain the exact template revision reference.

Status: REQUIRED BEFORE RENDERER IMPLEMENTATION.

## 15. Critical Finding: Finalized Document Reproducibility

A finalized PDF may depend on operation data, snapshots, template revision, branding assets, QR configuration, fonts, and source documents.

Define the minimum immutable inputs required to reproduce a generated PDF. At minimum this includes the finalized operation version, exact template revision, relevant immutable branding references/assets, and QR generation configuration/version.

Status: MUST RESOLVE BEFORE PRODUCTION PDF HISTORY.

## 16. Critical Finding: Free Appointment Slots

Free is a calculated availability state. Do not create thousands of empty appointment rows merely to display a calendar.

Configured availability generates candidate slots. Persist only actual appointment/reservation records.

Status: RESOLVED DIRECTION.

## 17. Critical Finding: Present to Operation Behavior

Appointment Type determines Present behavior. Present can record attendance only, or record attendance and create/start/offer an Operation.

Any created Operation retains the Appointment relation. One Appointment may link to multiple Operations.

Status: RESOLVED DIRECTION.

## 18. Critical Finding: Search and Shared Master Records

Access to a shared Person or Property master record must not imply access to every related Operation or Document.

Search authorization must operate at the result/resource level.

Status: RESOLVED SECURITY PRINCIPLE.

## 19. Critical Finding: Project Access Model

Define User, Project, Project Membership/Access, Role Assignment, global roles, and project-scoped roles.

Recommended direction: a user may have global permissions and project-scoped roles. Do not assume one global role is sufficient for multi-project operation.

Status: MUST RESOLVE BEFORE SECURITY SCHEMA FREEZE.

## 20. Architecture Gate

The project is ready to begin Foundation infrastructure:
- repository/application skeleton
- configuration
- FastAPI startup
- database engine/session
- Alembic infrastructure
- health endpoint
- test infrastructure
- basic error handling
- logging foundation

Do not freeze the complete business schema or implement irreversible business workflows until the critical decisions above are resolved.

## 21. Recommended Next Decision Batch

Resolve these seven items first:
1. Shared Person/Property ownership and project association
2. Exact immutable snapshot contents
3. Project Operation Type override matrix
4. Party-role cardinality/governance
5. Registration-number allocation policy
6. Contract-number uniqueness policy
7. Project/user role assignment model

After these seven are frozen:
1. revise DATABASE_SCHEMA.md
2. revise ERD.md
3. revise OPEN_DECISIONS.md
4. verify DOMAIN_MODEL.md
5. verify WORKFLOWS.md
6. freeze V1 schema
7. start Foundation Phase implementation

Do not start with UI screens before the underlying domain and authorization contracts are stable.