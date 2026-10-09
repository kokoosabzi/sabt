# SABT Project Skill

## Purpose
This file is the practical working skill for any coding agent contributing to SABT. Read it before making changes. It complements (and does not replace) `AI_AGENT_INSTRUCTIONS.md` and the architecture documents.

## Start Here
1. Read `README.md`.
2. Read `PROGRESS.md` to learn the current phase, verified status, and next task.
3. Read `AI_AGENT_INSTRUCTIONS.md`.
4. Read the domain-specific documents relevant to the task. For broad changes, read `ARCHITECTURE.md`, `DOMAIN_MODEL.md`, `WORKFLOWS.md`, `DATABASE_SCHEMA.md`, `ERD.md`, `SECURITY_AND_ROLES.md`, and `OPEN_DECISIONS.md`.
5. Inspect the existing implementation and migrations before changing them. Do not assume the code matches the specification.

## Source-of-Truth Order
1. Explicit decisions made by the user.
2. Explicit decisions recorded in project documents.
3. Domain invariants and accepted tests.
4. Existing implementation.
5. Agent assumptions.

If two authoritative documents conflict, stop and document the conflict. Do not silently invent a resolution.

## Product Boundaries
SABT is a Persian-first, local/LAN case and document management system for real-estate transfer/registration workflows. It is not an accounting/payment processor, marketplace, banking integration, or replacement for an official registry. Do not expand the product boundary without explicit approval.

## Technical Baseline
- Python, FastAPI, SQLAlchemy, Alembic, SQLite for V1.
- Server-side API is the security boundary; clients must never access SQLite directly.
- Filesystem-backed managed files with database metadata.
- Persian-first RTL UI; technical identifiers should display in LTR where appropriate.
- Keep the application lightweight and Windows/LAN-friendly.
- Every schema change requires an Alembic migration.
- Use aware UTC instants for stored timestamps; project timezone controls presentation and scheduling.
- Do not add a framework or service without a concrete requirement.

## Domain Invariants
- People and Properties are reusable master entities across projects.
- Project-specific property participation is represented by ProjectProperty, not by duplicating Property per project.
- Appointment and Operation are independent. Many-to-many links live in OperationAppointment.
- An Operation can have zero or one Contract; each Contract belongs to exactly one Property.
- Contract number is manually entered and is not a database primary key.
- Registration number is system-generated through a configured policy and transactionally allocated; never use MAX()+1.
- Operation Types can have global base definitions and project-specific activation/configuration.
- Party roles are dynamic. Retire used roles rather than deleting them.
- At Operation creation, create a working snapshot. At finalization, create immutable versioned snapshots.
- Finalized versions are canonical historical truth and must not be silently mutated.
- Corrections require request, approval, and a new version.
- Files are stored on the server; replacement is audited, archive is preferred to ordinary deletion, and physical deletion is Admin-only.
- Project isolation and resource authorization must be enforced on the backend for every request and search result.
- Backup means a full restorable snapshot, not only a database copy.

## Implementation Rules
- Keep business rules in service/domain layers, not in templates or browser JavaScript.
- Validate authorization, workflow, required data, restrictions, and concurrency server-side.
- Use short transactions for multi-step business actions. Services must clearly document whether the caller owns commit/rollback.
- Avoid partial side effects on validation failure. Validate inputs before writing whenever practical.
- Use optimistic locking/version checks for mutable records.
- Keep migrations deterministic and reversible where practical. Never silently drop data.
- Use explicit columns/tables for security- or business-critical configuration; reserve JSON for non-critical flexible presentation settings.
- Never log passwords, bearer tokens, signing keys, or unnecessary personal data.
- Use stable, safe error codes/messages; do not expose SQL, stack traces, or filesystem internals.
- Avoid adding dependencies unless they are needed and justified.

## Testing Contract
For every meaningful change:
1. Add or update tests covering the behavior and a likely failure path.
2. Run the focused tests, then the full suite when feasible.
3. Run migration upgrade checks against a fresh database and, where feasible, a representative existing database.
4. Report the exact commands and actual outcomes. Never claim tests passed if they were not run.
5. Add regression tests for bugs discovered during review.

Prioritize tests for:
- Authentication and deny-by-default authorization.
- Project isolation and cross-project resource access.
- Alembic upgrade/downgrade and ORM/migration parity.
- Number allocation, ambiguous policies, unsupported scopes/resets, and transaction rollback.
- Finalization invariants, immutable snapshots, optimistic locking, and correction/version flows.
- Appointment capacity/conflicts and OperationAppointment links.
- Document storage safety, replacement/archive, and full backup/restore.

## Change Workflow
1. Read PROGRESS.md and identify the active phase.
2. Select one small, coherent task that advances that phase.
3. Inspect affected code, schema, migrations, and tests.
4. State assumptions and unresolved decisions before coding when they materially affect behavior.
5. Implement the smallest complete change, including migration and tests where applicable.
6. Run tests and record actual results.
7. Update PROGRESS.md in the same change: tick completed work, add findings, list the next concrete task, and record commit/PR references if known.
8. If scope or architecture changes, update the relevant design documents too.
9. Keep work reviewable; prefer a branch and pull request for substantial changes. Do not merge or force-push without authorization.

## Progress File Rules
- PROGRESS.md is the living execution ledger, not a promise that unverified code works.
- Use [x] only for work completed and verified to the stated level.
- Use [ ] for incomplete, not-yet-verified, or blocked work.
- Distinguish “implemented” from “tests passed”.
- Record test commands and outcomes exactly. If no execution environment was available, say “Not run in this session”.
- At the end of every phase, write: delivered changes, verification evidence, remaining risks, and next phase.
- Keep completed historical entries; append a dated entry rather than rewriting history.

## Definition of Done
A task is done only when:
- Requirements and affected invariants are understood.
- Code and migrations are consistent.
- Relevant tests exist and have actually run, or the lack of execution is explicitly recorded as a blocker.
- Authorization and project isolation are reviewed.
- Error/rollback behavior is reviewed.
- Documentation and PROGRESS.md are updated.
- The agent reports changed files, test commands/results, remaining risks, and commit/PR identifiers.
