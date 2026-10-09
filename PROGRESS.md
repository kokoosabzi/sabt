# SABT Development Progress

> This file is the living execution ledger. A checked item means it is completed at the stated verification level, not merely planned. Never record tests as passing unless they were actually run.

## Current status

- **Current phase:** Phase 0 — Foundation audit and stabilization
- **Overall status:** In progress; repository implementation has not yet been verified by a local test run in this work session.
- **Current working rule:** Stabilize the existing foundation before adding more business features.

## Phase plan

### Phase 0 — Foundation audit and stabilization
- [ ] Run the existing test suite and record the real output.
- [ ] Verify that all Alembic migrations upgrade a fresh SQLite database successfully.
- [ ] Compare ORM metadata against migrations, including constraints, foreign keys, indexes, and nullability.
- [ ] Fix migration/model drift and add regression tests.
- [ ] Review auth/session expiry, revocation, password hashing, and deny-by-default authorization.
- [ ] Verify project isolation for every service and resource lookup.
- [ ] Test registration-number allocation for policy selection, ambiguity, scope, rollback, and concurrency assumptions.
- [ ] Review operation creation/finalization transaction boundaries and validation order.
- [ ] Update this file with verified findings and exact test commands.

### Phase 1 — Complete operation lifecycle
- [ ] Define and implement working snapshots at operation creation.
- [ ] Validate required parties, documents, fields, and workflow before finalization.
- [ ] Integrate registration-number allocation into finalization with safe rollback semantics.
- [ ] Include optional Contract and required historical data in operation snapshots.
- [ ] Add optimistic-locking checks to all mutating operation services.
- [ ] Add tests for finalization failures, success, idempotency/conflict, and immutable version snapshots.

### Phase 2 — Contracts and restrictions
- [ ] Implement Contract service and its exactly-one-Property invariant.
- [ ] Implement configurable Contract Number uniqueness scopes transactionally.
- [ ] Implement rule-based restriction evaluation and audited overrides.
- [ ] Add CSV/Excel/clipboard import staging, preview, validation, and transactional confirmation.
- [ ] Add tests for uniqueness scopes, restriction rules, import rollback, and authorization.

### Phase 3 — Documents and storage
- [ ] Implement safe filesystem storage service and logical storage keys.
- [ ] Implement document metadata, authorization, replacement, archive, and Admin-only physical deletion.
- [ ] Add size/type validation and SHA-256 integrity hashes.
- [ ] Add tests for traversal prevention, unauthorized access, replacement audit, and archival.

### Phase 4 — Appointments and reminders
- [ ] Implement appointment type behavior and configurable slot duration.
- [ ] Implement reservation capacity/conflict handling with concurrency protection.
- [ ] Implement Present/No-Show/Cancel/Done transitions and Operation links.
- [ ] Implement in-app reminders with deduplication and retry policy.
- [ ] Add tests for conflicting reservations, status transitions, and duplicate reminders.

### Phase 5 — Forms, templates, and PDF
- [ ] Implement immutable template revisions and activation validation.
- [ ] Implement approved data bindings only; never execute template-supplied code.
- [ ] Implement PDF generation and direct-print flow.
- [ ] Record exact template revision and immutable branding/QR inputs for reproducibility.
- [ ] Add rendering and historical reproducibility tests.

### Phase 6 — Search, UI, and administration
- [ ] Implement authorized search across supported entities.
- [ ] Build Persian RTL dashboard, operation stepper, quick navigation, and configuration screens.
- [ ] Add project/global role management and a documented permission matrix.
- [ ] Add UI/API integration tests for permission boundaries and project isolation.

### Phase 7 — Backup, restore, packaging, and release
- [ ] Implement full restorable snapshots with database, managed files, templates, branding, and generated documents.
- [ ] Add manifest, checksums, safe SQLite snapshot, atomic publication, and rotation.
- [ ] Implement Admin-only restore with mandatory pre-restore backup and post-restore validation.
- [ ] Package for Windows/LAN deployment and document installation/recovery.
- [ ] Run release checklist and restore drill.

## Verified baseline

### Repository work already committed
- [x] Architecture and domain documentation established.
- [x] FastAPI/SQLAlchemy/Alembic foundation files added.
- [x] Authentication, password hashing, session, and authorization foundation added.
- [x] Operation core service and version/snapshot structures added.
- [x] Appointment/Operation many-to-many model and migration added; redundant direct operation appointment column removed.
- [x] Initial transactional registration-number allocator added; currently supports only reset policy NEVER.

### Verification status
- [ ] Python test suite: **Not run in this session.**
- [ ] Fresh-database Alembic upgrade: **Not run in this session.**
- [ ] Alembic downgrade/upgrade round trip: **Not run in this session.**
- [ ] Numbering concurrency test: **Not run in this session.**
- [ ] ORM/migration parity check: **Not run in this session.**

## Known review items
- [x] Operation creation now validates a supplied Appointment before the first Operation write (commit `2e50f55`); regression/integration verification is still pending.
- [ ] Registration-number allocation exists but is not yet integrated into finalization.
- [ ] Finalization currently lacks required party/document/workflow/restriction validation.
- [ ] Snapshot at operation creation is not yet implemented.
- [ ] Finalization snapshot currently does not include Contract data.
- [ ] Numbering scope-key unit tests were added (`tests/test_numbering_unit.py`, commit `b2ad999`); tests have not been executed. Policy precedence and allowed persisted values still need tests/documentation.
- [ ] OperationTypeWorkflow uniqueness with nullable project_id needs review for SQLite NULL uniqueness behavior.
- [ ] Migration 0006 downgrade adds the legacy appointment_id column without restoring its former foreign-key behavior.
- [ ] Runtime database URL is currently hard-coded and should move to validated configuration before deployment.

## Decision log
- 2026-10-09: Added SKILL.md as the coding-agent operating contract and AGENTS.md as the repository entry point.
- 2026-10-09: Added this progress ledger. Test status remains explicitly unverified until a runner executes the commands.

## Latest phase entry

### Phase 0 — In progress (2026-10-09)
**Delivered:** agent guidance and progress tracking files.

**Verification evidence:** GitHub file creation commits only; no Python tests or migration commands were executed in this session.

**Remaining risks:** foundation correctness, migration parity, and service transaction boundaries remain unverified.

**Next task:** run the audit prompt in Codex against a separate branch, fix the highest-risk test/migration failures, and update this ledger with exact output.
