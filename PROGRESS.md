# SABT Development Progress

> This is the execution ledger. A checked item means it is complete at the stated verification level. Do not mark a feature implemented merely because its schema or design document exists.

## Current status

- **Current phase:** Phase 0 — Foundation audit and stabilization
- **Overall status:** Parent Contract creation, project-code immutability, atomic transfer numbering, and Buyer / Transferee-based current-owner derivation are implemented on `codex/foundation-audit`. CI run `38596512913` passed **87 tests, 2 warnings**, plus fresh SQLite upgrade and downgrade/re-upgrade through `0008_transfer_sequence_counter`. Implementation remains incomplete; PR #1 stays draft and unmerged.
- **Working rule:** Stabilize the foundation, make missing guarantees explicit, and do not resolve business-policy questions by guessing.

## Phase plan

### Phase 0 — Foundation audit and stabilization
- [ ] Review auth/session expiry, revocation, password hashing, and deny-by-default authorization beyond the current unit coverage.
- [ ] Verify project isolation for every service and resource lookup.
- [ ] Test registration-number allocation concurrency assumptions.
- [ ] Review operation creation/finalization transaction boundaries and validation order.
- [ ] Compare ORM metadata against migrations for tables, columns, nullability, foreign keys, and indexes/constraints.
- [x] Add CI for tests and fresh-database migration round-trip.
- [x] Add regression tests for authorization, session expiry/revocation, numbering behavior, operation project isolation, and ORM/migration parity.
- [x] Require active ProjectPerson membership before adding an OperationParty; reject missing, inactive, or cross-project membership before writes.
- [x] Require an expected operation version for party edits and finalization; reject stale party edits without side effects.
- [x] Record the verified findings and exact CI evidence in this progress ledger.

### Parent Contract schema foundation
- [x] Add additive Alembic migration for Project.contract_code, ParentContract, and Operation transfer-chain fields.
- [x] Add matching ORM models/constraints and update the logical ERD/database schema documentation.
- [x] Verify migration upgrade/downgrade/re-upgrade and ORM table/column/foreign-key/nullability parity in CI (run `38590960614`).
- [x] Add pure validation/formatting helpers and tests for two-digit Project contract codes, six-digit Parent Contract numbers, four-digit suffixes, and positive child sequences.\n- [ ] Integrate validation helpers into authorized Parent Contract creation and enforce project-code immutability after first use.
- [ ] Add transactional transfer child-number allocation on finalization; never use MAX()+1.
- [x] Add service tests for authorized Parent Contract creation, leading-zero preservation, missing project code, invalid suffixes, project membership/property association, duplicate suffix, and missing project access.
- [x] Add tests for project-code immutability, stale project versions, and invalid project contract codes.
- [ ] Add tests for transfer sequence uniqueness and rollback.

### Phase 1 — Complete operation lifecycle
- [ ] Define and implement working snapshots at operation creation.
- [ ] Validate required parties, documents, fields, and workflow before finalization.
- [ ] Integrate registration-number allocation into finalization with safe rollback semantics.
- [ ] Include optional Contract and required historical data in operation snapshots.
- [ ] Make optimistic-locking guarantees mandatory for mutating operation services where required.
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

### Implemented foundation components
- [x] Architecture/domain documentation and coding-agent guidance.
- [x] FastAPI, SQLAlchemy, Alembic model/migration foundation.
- [x] Password hashing, bearer sessions, and authorization foundation.
- [x] Operation create/party/finalize service skeleton and snapshot structures.
- [x] Operation–Appointment many-to-many association; redundant direct appointment FK removed.
- [x] Transactional registration-number allocator with policy/scope checks; currently supports reset policy `NEVER` only.
- [x] CI workflow runs pytest and Alembic upgrade/downgrade/re-upgrade checks on pushes and pull requests.

### Verified on GitHub Actions
- [x] On commit `e5a882401f62c1f68c302ea94c89783bff5ef73e`: **25 passed, 2 warnings**; Python test suite passed.
- [x] On commit `1b1903875e7ddcfe4bcfc2289324aafae9ad76a8`: **27 passed, 2 warnings**; added tests for inactive roles and revoked project access.
- [x] Fresh SQLite Alembic upgrade reached `0006_remove_operation_appointment_id (head)`.
- [x] Alembic downgrade to base and re-upgrade to head passed.
- [x] ORM/migration parity test passed for table names, column names, foreign keys, and column nullability (run `38343796388`, commit `1cc1ed2b946db611d7af6bbb751f7020fbd74fdc`).
- [x] Latest branch head `014e868cf88bd0e10332986abf081f2c25165319`: GitHub Actions run **38343582096 completed successfully**. This commit only updates progress documentation; the run verifies the current branch's CI workflow.
- [x] Latest test run `38343819274` succeeded on commit `1b1903875e7ddcfe4bcfc2289324aafae9ad76a8`: 27 tests passed, fresh migration succeeded, and downgrade/re-upgrade round trip succeeded.

## Known implementation gaps and risks

- [ ] Registration-number allocation is not integrated into finalization.
- [ ] Finalization does not yet validate required party/document/workflow/restriction rules.
- [ ] Working snapshot at operation creation is not implemented.
- [ ] Finalization snapshot does not include Contract data.
- [ ] Numbering concurrency has not been tested in this workstream.
- [ ] `OperationTypeWorkflow` uniqueness with nullable `project_id` needs review because SQLite permits multiple NULL values in unique keys.
- [ ] Migration 0006 downgrade re-adds legacy `appointment_id` without restoring the former foreign-key behavior.
- [ ] Runtime database URL is hard-coded as `sqlite:///./sabt.db`; validated environment configuration is still needed.
- [ ] Authorization guard currently accepts a fixed `project_id`; it does not yet resolve project scope dynamically from a request path/body.
- [ ] Optimistic locking is optional in current operation-service calls when `expected_version` is omitted.

## Decision log

- 2026-10-09: Added `SKILL.md`, `AGENTS.md`, and initial progress tracking.
- 2026-10-13: Added CI and expanded foundation regression tests on `codex/foundation-audit`.
- 2026-10-13: CI run `38343582096` passed for branch head `014e868cf88bd0e10332986abf081f2c25165319`.
- 2026-10-13: CI run `38343819274` passed with 27 tests, including revoked-project-access/inactive-role checks and schema nullability parity.
- 2026-10-13: CI run `38468577088` passed with 36 tests and SQLite migration upgrade/downgrade/re-upgrade checks. Added project-membership validation for OperationParty writes and mandatory optimistic version checks for party edits/finalization.
- 2026-10-13: Documented the Parent Contract / transfer Operation architecture proposal; implementation and numbering edge cases remain open.
- 2026-10-14: Added `create_parent_contract` and `set_project_contract_code` services on `codex/foundation-audit`, including authorization, project/person/property association checks, string-safe six-digit number creation, duplicate safeguards, optimistic project version checks, and project-code immutability after first use.
- 2026-10-14: Added migration `0008_transfer_sequence_counter`, the ParentContract counter, validation when linking an Operation to a Parent Contract, atomic child-number allocation during finalization, and rollback/sequential-number tests. CI run `38594111665` passed 85 tests and the migration upgrade/downgrade/re-upgrade round-trip through `0008_transfer_sequence_counter`.

## Parent Contract transfer-chain design update — 2026-10-13

- [x] Recorded the proposed stable six-digit Parent Contract root and per-transfer child business number convention in architecture/domain/workflow/schema documents.
- [x] Confirmed Project codes are two numeric digits starting at `10`; `01`–`09` are not used. The code is shared by all members/contracts in a Project.
- [x] Confirmed the four-digit parent suffix may be entered manually or imported from Excel/CSV; imports may also include optional unit/property details.
- [x] Distinguished a genuine transfer (new Operation) from a correction to an existing finalized transfer (OperationVersion/correction workflow).
- [x] Documented parent-number search/history, current-owner derivation, transactional child numbering, and staged Excel/CSV import as design targets.
- [ ] Resolve the remaining business decisions: global uniqueness/immutability of Project codes, child-number gaps/width, ownership-effective state, legacy import ordering, and exact import columns/person duplicate matching.
- [x] Implement schema and core service behavior for Parent Contract creation and child-number allocation.
- [ ] Implement current-owner derivation from latest valid finalized transfers; recipient/owner role policy must be explicitly defined rather than guessed.
- [ ] Add authorized search/history APIs, UI, and staged Excel/CSV import.

## Next task

Define how the transferee is identified in operation parties and implement current-owner/history queries; keep the pull request open and unmerged until the new checks and risks are reviewed.


## Confirmed ownership rule — 2026-10-14
- [x] User confirmed the owner-changing party role is **Buyer / Transferee**.
- [x] Canonical role code is `BUYER_TRANSFEREE`; a Parent Contract transfer cannot be finalized without at least one active party with this role.
- [x] Current owner is derived from the latest valid finalized transfer with a finalized current OperationVersion and Buyer / Transferee party; draft operations do not change ownership.
- [x] Parent Contract history response includes the current owner and identifies whether it came from the initial contract or a finalized transfer.
- [ ] Verify latest CI for the buyer/transferee rule and current-owner derivation; then expose the history service through an authorized API route.


## API and management reporting update — 2026-10-14
- [x] Added authenticated `GET /contracts/parent/{contract_number}/history` route using the authorized service; maps invalid number, missing contract, and forbidden access to HTTP 422/404/403.
- [x] Registered the contract-history router in the FastAPI app.
- [x] Specified a Persian RTL management portal, daily/date-range workflow reports, contract transfer-chain report, ad-hoc reports, drill-down behavior, permissions, timezone/Jalali date handling, pagination, and export/audit rules in `UI_FLOW.md`.
- [x] Add API tests for contract-history route authentication, authorization, invalid numbers, not-found responses, and response shape.
- [ ] Implement portal summary/report APIs only from verified source data and enforce project scope in every query.
- [ ] Implement contract-history UI and portal/report screens; the repository currently has no frontend application files.
- [ ] Implement staged Excel/CSV import with validation, preview, explicit confirmation, transactional persistence, and import result report.
- [ ] Keep PR #1 draft and do not merge until tests and review are complete.

- [x] GitHub Actions run [38602455911](https://github.com/kokoosabzi/sabt/actions/runs/38602455911) passed on API route/test commit `814f87851f9c439bb66c22b83e6f5d255088834d`; the CI workflow includes the full pytest suite and SQLite migration round-trip.



## Reporting implementation (2026-10-15)
- [x] Add project-scoped management summary indicators and paginated workflow report queries with status/type/contract/property/creator filters.
- [x] Expose `/reports/management/summary` and `/reports/workflow`; retain `/reports/management-summary` as a deprecated compatibility alias.
- [x] Add service tests and a check that report routes are registered.
- [x] Add route-level tests for report permissions, range validation, empty metrics and paginated results.
- [x] Verify GitHub Actions run [38635961043](https://github.com/kokoosabzi/sabt/actions/runs/38635961043): 104 tests passed; SQLite upgrade, Alembic head, downgrade and re-upgrade passed.
- [ ] Add state-transition audit events before reporting historical status changes or time-in-state.


## Management and workflow reports — 2026-10-15
- [x] Implement project-scoped management summary from stored operation and Parent Contract records.
- [x] Implement a paginated workflow report with time range, status, operation type, Parent Contract/child number, property and creator filters.
- [x] Expose authenticated report endpoints; permission checks and project scope are enforced in the service.
- [x] Add report service/API tests and fix route-registration test compatibility with current FastAPI.
- [x] CI run [38635961043](https://github.com/kokoosabzi/sabt/actions/runs/38635961043) passed: 104 tests, 2 warnings; fresh SQLite migration, Alembic head, downgrade and re-upgrade checks also passed.
- [ ] Add workflow event history before reporting historical status changes or time-in-state.
- [ ] Build the Persian RTL portal and report pages; add CSV/Excel/PDF export after UI/API contract review.
