# SABT — Remaining Design Decisions

Version: 0.2

These points remain intentionally open. Resolved V1 decisions are recorded below.

1. Contract lifecycle: exact creation/detachment/correction rules remain open. Architecture direction agreed for design: a stable six-digit Parent Contract anchors a chain of transfer Operations, each with its own child business number (for example `109876/1`, `109876/2`). This is not yet implemented; finalize the edge cases listed under “Parent/child transfer-chain proposal” before schema migration.
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



## Parent/child transfer-chain proposal — architecture direction, 2026-10-13

The proposed business model is accepted as the direction for the next design pass, but not yet marked implemented:

- A Parent Contract has a stable six-digit business number. Its first two digits represent a Project code; the remaining four digits identify the parent within the applicable numbering namespace.
- A Parent Contract can have zero or many transfer Operations. Each finalized transfer is a separate Operation and receives a child business number such as `109876/1`, `109876/2`, or `109876/10`.
- A correction/revision of an already finalized transfer is an OperationVersion/correction workflow, not a new transfer child. A genuine subsequent transfer is a new Operation.
- Parent/child business numbers are identifiers, never database primary keys. Allocate child sequence numbers transactionally per parent; never use `MAX()+1`.
- Searching the parent number should return the parent summary, ordered transfer history, and authorized detail navigation for each child. Current ownership is derived only from the latest valid finalized transfer under an explicitly defined validity policy.
- Excel/CSV import must support a staged mapping, validation/duplicate report, preview, explicit confirmation, transactional persistence, and an audit/import report. A partial import must not be presented as successful.

Before implementation, decide: (1) whether Project codes are exactly two numeric digits and globally unique; (2) how the four-digit parent suffix is assigned and how existing numbers are preserved; (3) child numbering gaps/cancellation policy and whether there is any width limit; (4) the precise state transition at which a transfer becomes ownership-effective; (5) how imported legacy transfer histories and their ordering are represented.

The proposal changes the domain relationship: the existing “zero or one Contract per Operation” remains valid for an Operation's transaction-specific Contract record, but the parent chain must be represented separately and must not be inferred from that optional Contract link alone.
