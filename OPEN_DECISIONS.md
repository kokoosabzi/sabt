# SABT — Remaining Design Decisions

Version: 0.3

This file tracks genuinely unresolved product/security decisions. The Parent Contract defaults below are frozen for the first additive schema implementation; they do not mean the feature is already implemented.

## Open decisions

1. Exact Registration Number policy values: scope, prefix, sequence width, reset behavior and allocation timing.
2. Complete permission matrix and exact global/project scope of each permission.
3. Storage retention for temporary files, generated PDFs, archived documents, physical deletions and backups.
4. Reminder delivery mechanism and retry/deduplication policy in V1.
5. Search fields, filters and ranking.
6. Backup encryption/key management and secret recovery.
7. Exact authentication/session mechanism and password/account policy.
8. Template asset revision storage and exact PDF reproducibility manifest.
9. Exact custom-field scope precedence where global, project and Operation-Type definitions overlap.
10. Legacy transfer import: what source fields prove historical order and how ambiguous or tied records are handled. Never guess ordering from import row order unless the user explicitly confirms that rule.
11. Import matching policy for existing people and properties, including how duplicate candidates are resolved. Never silently merge master records.
12. Exact import template columns and required/optional fields. Keep the first import implementation narrow and versioned; optional property details must not make the Parent Contract number ambiguous.

## Resolved V1 decisions

1. Person and Property are central reusable master records. Project-specific association/context is separate.
2. Finalized OperationVersion is the canonical immutable historical snapshot; structured snapshots support queryability.
3. Critical Operation Type behavior is configured through explicit project-scoped structures; opaque JSON is not authoritative for workflow/numbering/required-document rules.
4. Party roles are dynamic; duplicate role assignments are allowed; Operation Type defines required role cardinality; used roles are retired, not deleted.
5. Registration numbers use explicit NumberingPolicy + NumberingState and transactional allocation; never MAX()+1.
6. Contract-number uniqueness is explicitly GLOBAL, PROJECT, OPERATION_TYPE, or NONE and is enforced transactionally.
7. Users may have global and project-scoped roles. Project access is separately represented and required for project-scoped actions.
8. V1 timezone policy: store timezone-aware UTC instants; Project carries the business/presentation timezone; server-local timezone is never an implicit rule.

## Parent Contract / transfer-chain decisions — frozen defaults, 2026-10-14

These decisions resolve the schema-level ambiguities for the initial implementation:

- **Separate numbering field:** preserve the existing `Project.code` as-is because it currently accepts general strings and may already be used by existing data. Add a distinct nullable `Project.contract_code` for Parent Contract numbering. It is a two-character numeric string from `10` through `99`; `01`–`09` are invalid. It must be unique when present. Do not auto-convert or renumber existing project codes. New Parent Contracts require a valid contract code.
- **Stability:** once a Project has any Parent Contract, its `contract_code` cannot be changed or cleared. Before it is used, changing it remains an audited administrative operation; uniqueness is still enforced.
- **Parent number:** preserve the six-character string exactly: two-character Project contract code plus a four-digit suffix. Suffixes `0000`–`9999` retain leading zeroes. The business number is not a database primary key and is globally unique.
- **Transfer sequence:** child numbers use positive decimal integers without zero padding (e.g. `/1`, `/2`, `/10`). Allocate a sequence transactionally when a transfer is finalized, never with `MAX()+1`. Once a child number has been issued, never reuse it, even if that transfer is later reversed/cancelled; gaps are expected.
- **Ownership:** only a finalized transfer changes the derived current owner. Draft, rejected, or cancelled-before-finalization operations do not. A later reversal/corrective business event must be represented explicitly and finalized; never rewrite the prior finalized history to make it disappear. Exact reversal operation types can be configured later.
- **Correction vs transfer:** correcting the record of an already finalized operation is a revision/correction of that operation and must preserve its audit/history; a genuine subsequent ownership transfer is a new Operation with a new child number.
- **Property details:** Parent Contract may optionally reference a Property. Imported unit/property columns are optional context, not part of the six-digit identifier.
- **Import safety:** import is staged (map → validate/deduplicate → preview → explicit confirm → transactionally persist → report). No silent renumbering, no silent Person/Property merge, and no success response for a partial write. Historical ordering and ambiguous identity matching remain open as listed above.

The Parent Contract is a distinct entity from the existing optional transaction-specific `Contract` row. A transfer chain must be linked explicitly and must not be inferred from `Contract.operation_id` or `OperationVersion` alone.

## Status note

The decisions above are architecture defaults only. The Parent Contract schema, migrations, services, UI, import pipeline and ownership query are **not implemented yet**. The foundation branch remains a draft PR and must stay unmerged until tests and migration round-trip pass.
