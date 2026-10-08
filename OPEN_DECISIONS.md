# SABT — Remaining Design Decisions

Version: 0.2

These points remain intentionally open. Resolved V1 decisions are recorded below.

1. Contract lifecycle: creation, detachment and correction relationship with Operation.
2. Exact Registration Number policy values: scope, prefix, sequence width, reset behavior and allocation timing.
3. Complete permission matrix and exact global/project scope of each permission.
4. Storage retention for temporary files, generated PDFs, archived documents, physical deletions and backups.
5. Reminder delivery mechanism and retry/deduplication policy in V1.
6. Search fields, filters and ranking.
7. Backup encryption/key management and secret recovery.
8. Exact authentication/session mechanism and password/account policy.
9. Template asset revision storage and exact PDF reproducibility manifest.
10. Exact custom-field scope precedence where global, project and Operation-Type definitions overlap.

## Resolved V1 decisions — 2026 architecture freeze batch

The following decisions are frozen for V1 and should no longer be treated as open:

1. Person and Property are central reusable master records. Project-specific association/context is separate.
2. Finalized OperationVersion is the canonical immutable historical snapshot; structured snapshots support queryability.
3. Critical Operation Type behavior is configured through explicit project-scoped structures; opaque JSON is not authoritative for workflow/numbering/required-document rules.
4. Party roles are dynamic; duplicate role assignments are allowed; Operation Type defines required role cardinality; used roles are retired, not deleted.
5. Registration numbers use explicit NumberingPolicy + NumberingState and transactional allocation; never MAX()+1.
6. Contract-number uniqueness is explicitly GLOBAL, PROJECT, OPERATION_TYPE, or NONE and is enforced transactionally.
7. Users may have global and project-scoped roles. Project access is separately represented and required for project-scoped actions.
8. V1 timezone policy: store timezone-aware UTC instants; Project carries the business/presentation timezone; server-local timezone is never an implicit rule.

Remaining open items include the exact authentication/session implementation, complete permission catalog, backup encryption/key management, retention defaults, reminder delivery details, search ranking, template asset revision storage, and other implementation-level policies.

