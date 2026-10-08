# SABT — Remaining Design Decisions

Version: 0.1

These points remain intentionally open and must be decided before database schema is frozen.

1. Contract lifecycle: creation, detachment and correction relationship with Operation.
2. Registration number scope, prefix, sequence width, reset behavior and allocation rules.
3. Contract-number uniqueness policy and its allowed scopes.
4. Which Operation Type properties can be overridden per Project.
5. Party-role governance, including required roles and whether duplicate roles are allowed.
6. Complete permission matrix.
7. Exact immutable snapshot field sets for Person, Property, Party and Operation.
8. Atomic numbering behavior under concurrent users.
9. Storage retention for temporary files, generated PDFs, archived documents, physical deletions and backups.
10. Reminder delivery mechanism in V1; in-app notifications are sufficient unless external channels are later requested.
11. Timezone policy for backend timestamps and local presentation.
12. Search fields, filters and ranking.


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
