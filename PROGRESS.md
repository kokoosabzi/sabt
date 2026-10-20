# SABT Development Progress

> This is the execution ledger. A checked item means it is complete at the stated verification level. Do not mark a feature implemented merely because its schema or design document exists.

## Current status — reconciled 2026-10-20 (after PR #42)

- **Current phase:** Phase 0 — Foundation audit and stabilization. Reporting/UI additions are available, but they do not replace the foundational lifecycle, security, and data-integrity gates below.
- **Current `main` code milestone:** `5d7732e6777067af75f5ddec41a2c33ade9ccbb7` (PR #42 adds configured sequential operation workflow transitions and finalization readiness enforcement; PR #38 adds end-to-end auth API lifecycle tests; PR #36 bounds password-hash verification parameters; PR #34 tests operation transaction rollback; PR #32 verifies concurrent registration-number allocation).
- **Latest verified CI:** [run 39488009480](https://github.com/kokoosabzi/sabt/actions/runs/39488009480) passed on the final PR #42 code head: full tests, Chromium browser E2E, fresh SQLite migration upgrade, Alembic head, downgrade, and re-upgrade checks all passed.
- **Merged milestones:** PR #1 foundation/import stabilization; PR #7 Jalali calendar and controlled time selectors; PR #8 permission-scoped Excel exports; PR #9 print-ready report views. See the historical entries below for feature-specific CI evidence.
- **Implemented on `main`:** Parent Contract create/history/current-owner derivation and staged CSV/XLSX import; initial Persian RTL portal; management/workflow/event reports; CSV/XLSX exports; Jalali report date picker and project-timezone conversion; browser print-to-PDF views.
- **Still incomplete:** comprehensive workflow-event coverage; full operation lifecycle guarantees beyond the newly enforced transition/finalization-readiness path; full Contract/restriction services; managed document storage; appointments/reminders; template designer and server-side reproducible PDF generation; full search/admin UI; backup/restore and packaging.
- **Working rule:** Treat current code, tests, and migration evidence as implementation facts; treat architecture documents as requirements. Do not infer unrecorded events or time-in-state. Do not guess unresolved business rules.
- **Merge rule:** After a focused change passes required CI/tests and review, merge it promptly; do not leave stable PRs open by default. Never merge failing or unverified work.

> Historical notes below are retained as an audit trail. Where an older unchecked item or status statement conflicts with this reconciled section or a later dated entry, treat it as superseded and update it when its section is next touched.

## Phase plan

### Phase 0 — Foundation audit and stabilization
- [x] Review authentication/session expiry, revocation, password hashing, and deny-by-default authorization for the currently exposed API surface: service/unit tests cover project access and roles, API tests cover login/me/logout, expired/revoked sessions, inactive accounts, and invalid credentials, and password verification rejects unbounded stored scrypt parameters (PRs #36 and #38; CI passed in [run 39329277841](https://github.com/kokoosabzi/sabt/actions/runs/39329277841)).
- [x] Bound password-hash verification to the supported scrypt cost parameters and salt/digest lengths so malformed stored values cannot request unbounded derivation work (PR #36; CI passed in [run 39328523927](https://github.com/kokoosabzi/sabt/actions/runs/39328523927)).
- [ ] Verify project isolation for every service and resource lookup.
- [x] Scope parent-contract history, current-owner derivation, and report joins to the owning project, with cross-project regression tests (PR #15; CI passed in [run 39148879162](https://github.com/kokoosabzi/sabt/actions/runs/39148879162)).
- [x] Harden current-owner person lookups against inconsistent legacy links lacking ProjectPerson membership; foreign-project transferees and missing initial-owner membership are covered by regression tests (PR #16; CI passed in [run 39152941082](https://github.com/kokoosabzi/sabt/actions/runs/39152941082)).
- [x] Verify registration-number allocation under four concurrent independent SQLite sessions; allocations were unique and the persisted sequence counter matched the successful allocation count (PR #32; CI passed in [run 39326782286](https://github.com/kokoosabzi/sabt/actions/runs/39326782286)).
- [x] Review operation creation/finalization transaction boundaries and validation order; explicitly document caller-owned commit/rollback and test rollback of draft creation links/events plus transfer sequence, status, snapshots, version rows, and finalization events (PR #34; CI passed in [run 39327559692](https://github.com/kokoosabzi/sabt/actions/runs/39327559692)).
- [x] Reject inactive Property records during operation creation, with a regression test that verifies no Operation row is written (PR #11; CI passed in [run 39147040578](https://github.com/kokoosabzi/sabt/actions/runs/39147040578)).
- [x] Revalidate Property, ProjectProperty association, Person, ProjectPerson membership, and PartyRole active/retired state before finalization side effects (PR #12; CI passed in [run 39147926546](https://github.com/kokoosabzi/sabt/actions/runs/39147926546)).
- [x] Validate registration-number format configuration before sequence state changes (PR #13; CI passed in [run 39148105940](https://github.com/kokoosabzi/sabt/actions/runs/39148105940)). PR #14 also rejects attribute access in templates before sequence state changes; CI passed in [run 39148808964](https://github.com/kokoosabzi/sabt/actions/runs/39148808964).
- [x] Compare ORM metadata against migrations for tables, columns, nullability, foreign keys, unique constraints, CHECK constraints, and explicit indexes; the parity test also treats SQLite unique indexes as equivalent uniqueness enforcement (PR #30; CI passed in [run 39325948273](https://github.com/kokoosabzi/sabt/actions/runs/39325948273)).
- [x] Enforce project-scoped composite foreign keys for operation property/parent-contract references and parent-contract initial-person/property references (PR #17; CI passed in [run 39153566324](https://github.com/kokoosabzi/sabt/actions/runs/39153566324)).
- [x] Bind workflow events to the same project as their operation with a composite foreign key and cross-project regression test (PR #19; CI passed in [run 39157027847](https://github.com/kokoosabzi/sabt/actions/runs/39157027847)).
- [x] Bind each OperationParty to both its operation project and a ProjectPerson membership through composite foreign keys; migration preflights existing data rather than inventing missing memberships (PR #21; CI passed in [run 39297451554](https://github.com/kokoosabzi/sabt/actions/runs/39297451554)).
- [x] Enforce same-project appointment-operation junctions with composite foreign keys and reject legacy cross-project links during migration preflight (PR #23; CI passed in [run 39298120817](https://github.com/kokoosabzi/sabt/actions/runs/39298120817)).
- [x] Scope person/property snapshots to the owning operation project, enforce snapshot party/person and operation/property consistency, and preflight legacy snapshot rows (PR #25; CI passed in [run 39298821916](https://github.com/kokoosabzi/sabt/actions/runs/39298821916)).
- [x] Require every operation to reference an operation type configured for the same project, with a composite foreign key and migration preflight (PR #27; CI passed in [run 39299732784](https://github.com/kokoosabzi/sabt/actions/runs/39299732784)).
- [x] Bind Contract rows to the project and property of their source operation, with a migration preflight for inconsistent existing rows (PR #29; CI passed in [run 39300745345](https://github.com/kokoosabzi/sabt/actions/runs/39300745345)).
- [x] Reject existing bearer sessions when their user account is deactivated (PR #18; post-merge CI passed in [run 39156896547](https://github.com/kokoosabzi/sabt/actions/runs/39156896547)).
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
- [x] Freeze Project contract-code rules: unique two-digit codes from `10` to `99`; a code cannot be changed or cleared after a Parent Contract uses it.
- [x] Freeze child numbering as positive decimal suffixes (`/1`, `/2`, `/10`); allocation is transactional and issued child numbers are never reused.
- [x] Confirm ownership changes only from a valid finalized transfer and the `BUYER_TRANSFEREE` role; draft/non-finalized operations do not change the current owner.
- [ ] Resolve remaining import policy questions: legacy historical ordering, duplicate Person/Property matching, and whether later import-template versions should accept additional source columns.
- [x] Implement Parent Contract schema, create service, child-number allocation, authorized history/current-owner query, and staged CSV/XLSX import with preview, revalidation, explicit confirmation, and transaction rollback coverage.
- [x] Expose authorized Parent Contract history and current-owner information in the reporting portal.

## Next task

Continue Phase 0 foundation audit: verify authorization/project isolation across service and resource lookups, operation creation/finalization transaction boundaries, registration-number allocation rollback/concurrency assumptions, and ORM/migration parity. Keep event-coverage limitations explicit; do not report time-in-state until all relevant transitions are persisted.


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
- [x] Implement portal summary/report APIs from verified stored data with project-scope and permission checks.
- [x] Implement initial contract-history UI and Persian RTL portal/report screens; advanced UI and browser end-to-end tests remain.
- [ ] Implement staged Excel/CSV import with validation, preview, explicit confirmation, transactional persistence, and import result report.
- [ ] Keep PR #1 draft and do not merge until tests and review are complete.

- [x] GitHub Actions run [38602455911](https://github.com/kokoosabzi/sabt/actions/runs/38602455911) passed on API route/test commit `814f87851f9c439bb66c22b83e6f5d255088834d`; the CI workflow includes the full pytest suite and SQLite migration round-trip.



## Reporting implementation (2026-10-15)
- [x] Add project-scoped management summary indicators and paginated workflow report queries with status/type/contract/property/creator filters.
- [x] Expose `/reports/management/summary` and `/reports/workflow`; retain `/reports/management-summary` as a deprecated compatibility alias.
- [x] Add service tests for metrics, project permission, range validation, filters and pagination, plus route-registration checks.
- [x] Add route-level tests for report permissions, range validation, empty metrics and paginated results.
- [x] Verify GitHub Actions run [38636249232](https://github.com/kokoosabzi/sabt/actions/runs/38636249232): 105 tests passed; fresh SQLite upgrade, Alembic head, downgrade and re-upgrade passed.
- [x] Check report authorization before resolving the requested Project, avoiding disclosure of inaccessible Project existence; add a cross-project regression test.
- [x] Add WorkflowEvent records for operation creation/finalization and a project-scoped, paginated `/reports/workflow/events` API; report only persisted events.
- [ ] Extend event capture to all relevant lifecycle changes (party edits, cancellation/rejection, assignments and appointment transitions) before claiming comprehensive workflow history or time-in-state.


## Management and workflow reports — 2026-10-15
- [x] Implement project-scoped management summary from stored operation and Parent Contract records.
- [x] Implement a paginated workflow report with time range, status, operation type, Parent Contract/child number, property and creator filters.
- [x] Expose authenticated report endpoints; permission checks and project scope are enforced in the service.
- [x] Add report service/API tests and fix route-registration test compatibility with current FastAPI.
- [x] CI run [38635961043](https://github.com/kokoosabzi/sabt/actions/runs/38635961043) passed: 104 tests, 2 warnings; fresh SQLite migration, Alembic head, downgrade and re-upgrade checks also passed.
- [x] Add workflow event history endpoint based on persisted events; no inferred events or hidden time-in-state estimates.
- [ ] Extend event recording to every relevant workflow transition before offering a comprehensive event timeline.
- [ ] Build the Persian RTL portal and report pages; add CSV/Excel/PDF export after UI/API contract review.

- [x] Require timezone-aware report range bounds and normalize them to UTC; add malformed parent/child contract filter validation.
- [x] Add dashboard counts for currently open operations and parent-contract transfers finalized in the selected period, without inferring unrecorded state transitions.
- [x] Latest verification: [GitHub Actions run 38636446498](https://github.com/kokoosabzi/sabt/actions/runs/38636446498) passed **105 tests, 2 warnings**, plus fresh SQLite upgrade, Alembic head, downgrade and re-upgrade checks.


## Workflow event audit stream — 2026-10-15
- [x] Add migration `0009_workflow_events` and matching `WorkflowEvent` ORM model with project/operation/actor references and time indexes.
- [x] Record `OPERATION_CREATED`, `PARTY_ADDED`, and `OPERATION_FINALIZED` in the same database transaction as their source actions.
- [x] Add project-scoped, time-filtered, paginated `GET /reports/workflow/events` using event occurrence time rather than operation creation time.
- [x] Document the event table, transaction behavior, and current event coverage in `DATABASE_SCHEMA.md`.
- [x] Verify CI run [38636861666](https://github.com/kokoosabzi/sabt/actions/runs/38636861666): 106 tests passed; migration upgrade/downgrade/re-upgrade checks passed.
- [x] Verify latest CI run [38637141106](https://github.com/kokoosabzi/sabt/actions/runs/38637141106): 106 tests passed, including registration of the event report endpoint; SQLite migration round-trip passed.
- [ ] Extend event recording to every implemented workflow state transition as the workflow engine grows; do not report time-in-state until all required transitions and timestamps are persisted.
- [ ] Build the Persian RTL portal UI after the foundation stabilization gate; the repository currently has no frontend application.

- [x] Latest workflow-event verification: [GitHub Actions run 38636873310](https://github.com/kokoosabzi/sabt/actions/runs/38636873310) passed **106 tests, 2 warnings**, including fresh SQLite migration and downgrade/re-upgrade checks.

- [x] Add API regression coverage for `GET /reports/workflow/events` and ensure both event and linked Operation queries are scoped to the authorized project.
- [x] Latest verified branch checks: [GitHub Actions run 38637248974](https://github.com/kokoosabzi/sabt/actions/runs/38637248974) passed **107 tests, 2 warnings**, plus fresh SQLite migration, Alembic head, downgrade and re-upgrade checks.


## Persian reporting portal UI — 2026-10-16
- [x] Add responsive Persian RTL interface at `/portal/` with login/logout, management summary, paginated workflow report, persisted workflow events and Parent Contract history lookup.
- [x] Add a smoke test confirming the portal is served as Persian RTL HTML.
- [x] GitHub Actions run [38881571821](https://github.com/kokoosabzi/sabt/actions/runs/38881571821) passed on the portal implementation commit; the workflow runs pytest and SQLite migration round-trip checks.
- [x] Add permission-scoped CSV exports for workflow and workflow-event reports, with UTF-8 BOM for Persian text and a 5,000-row export ceiling.\n- [x] Add Excel exports, Jalali calendar/time controls, and project-timezone-aware date display (completed in later entries below).
- [x] Add Chromium browser E2E coverage for critical reporting/import flows.
- [ ] Add a dedicated graphical transfer-tree visualization; current portal supports parent-contract history lookup but this does not imply a full graphical tree.


## CSV report exports — 2026-10-17
- [x] Add `GET /reports/workflow/export.csv` and `GET /reports/workflow/events/export.csv`, reusing the report service's project and permission checks.
- [x] Preserve filters and time bounds in exported data; export all matching rows up to 5,000 and reject larger exports instead of silently truncating them.
- [x] Emit UTF-8 CSV with BOM for Persian-compatible spreadsheet opening and safe CSV escaping via Python's csv writer.
- [x] Add portal download buttons for workflow and event reports; downloads reuse the visible filters and bearer session.
- [x] Add tests for CSV encoding, response headers, and project access denial.
- [x] GitHub Actions run [39053557591](https://github.com/kokoosabzi/sabt/actions/runs/39053557591) passed after fixing the BOM test expectation. PR validation is being checked separately.
- [x] Neutralize spreadsheet formula injection in text cells beginning with `=`, `+`, `-` or `@`; add a regression test.

- [x] Added a regression test for spreadsheet formula injection protection in commit `df5751b3b3a5cbc7ca58ea5885624499ff39905f`; final CI verification is pending.


## Project-timezone reporting update — 2026-10-17
- [x] Added authenticated `GET /reports/project-context?project_id=...`; it returns the project's configured timezone only to users who have dashboard or workflow-report permission and active project access.
- [x] Reject invalid configured timezone identifiers rather than silently displaying timestamps in another timezone.
- [x] Updated the portal to format displayed timestamps in the selected project's IANA timezone.
- [x] Updated datetime-local report filters to interpret entered wall-clock times in the project's timezone and convert them to UTC before calling report APIs; nonexistent local times caused by timezone transitions are rejected with a user-facing message.
- [x] Default report range is now initialized in project-local time after authorized project context loads.
- [x] Added API tests for timezone context, workflow-only permission, and denial without report permissions.
- [x] CI run [39054310436](https://github.com/kokoosabzi/sabt/actions/runs/39054310436): test suite passed; fresh SQLite migration, Alembic head, downgrade and re-upgrade steps all passed on commit `338e414d10a017ea0c82f80c812010b83c4cace8`.
- [x] Superseded by the shared Jalali date/time picker standard recorded below; report dates are selected from a Jalali calendar and time uses controlled hour/minute selectors.

## Latest work — staged contract import API

- [x] Bulk-import feature browser end-to-end automation is implemented and verified on Chromium.
- [x] Added a bounded CSV/XLSX parser for parent-contract import rows (`suffix`, `initial_person_id`, optional `property_id`), including strict column checks, row limits, file-size limits, and row-level format validation.
- [x] Added an authenticated preview endpoint that checks project authorization, project status/code, existing duplicates, active people/project membership, and optional property/project association without writing records.
- [x] Added a confirmation endpoint that revalidates client-submitted rows and attempts all contract creations within one transaction; it relies on existing parent-contract service rules and database constraints.
- [x] Added parser tests for CSV/XLSX success, invalid columns/data, unsupported file types, encoding, empty data, and size limits.
- [x] Added a Persian RTL portal page for file selection, preview table, validation issues, explicit confirmation, and success/error feedback.
- [x] Added API tests for preview-without-writes, successful confirmation, duplicate rows, and missing create permission.
- [x] Added API regression tests that force a failure on the second row and simulate a uniqueness conflict arising after preflight; both assert that the entire batch is rolled back with zero persisted contracts.
- [x] Added inline editable fields for suffix, initial person ID, and optional property ID in the preview table, plus a no-write `/contracts/parent/import/validate` endpoint to refresh duplicate and association checks after edits.
- [x] Added API regression coverage proving duplicate suffixes can be corrected and revalidated without creating records, plus a portal smoke test for the inline-edit/revalidate controls.
- [x] Inline preview correction and server-side revalidation are implemented and covered by API/UI smoke tests; malformed file structure/columns still require fixing the source file and uploading again.
- [x] Hardened parser resource limits: CSV rows are processed incrementally, the 2,000-row cap is enforced during parsing, duplicate/blank headers and mismatched row widths are rejected, and XLSX archives are screened for encryption, excessive ZIP entries, and expanded size above 50 MiB.
- [x] Added regression tests for malformed CSV headers/rows, the row cap, and invalid XLSX ZIP content.
- [x] CI run [39055555558](https://github.com/kokoosabzi/sabt/actions/runs/39055555558) passed: **135 tests passed**, plus fresh SQLite migration, Alembic head, downgrade and re-upgrade checks.
- [x] Added a real Playwright/Chromium browser E2E covering sign-in, CSV selection, duplicate preview, inline correction, server revalidation, explicit confirmation, and persisted contract-number verification.
- [x] GitHub Actions run [39055125021](https://github.com/kokoosabzi/sabt/actions/runs/39055125021) passed on commit `583878d27e93b75c71ebf00e657fe58f5bed4c3d`: **128 tests passed**, fresh SQLite migration upgrade, Alembic head verification, and downgrade/re-upgrade all succeeded (2 deprecation warnings).
- [x] GitHub Actions run [39055134348](https://github.com/kokoosabzi/sabt/actions/runs/39055134348) also passed on the latest documentation commit `f18768092ceb1a925e9fe1eb00266b4f121bd214`.
- [x] GitHub Actions run [39055279448](https://github.com/kokoosabzi/sabt/actions/runs/39055279448) passed after inline correction and UI smoke-test additions: **130 tests passed**, fresh SQLite upgrade, Alembic head, downgrade, and re-upgrade all succeeded.
- [x] Latest progress-documentation CI run [39055286369](https://github.com/kokoosabzi/sabt/actions/runs/39055286369) passed on commit `cb8606c253057654bea74f5be636eed52f14c253`.
- [x] Browser E2E verified in CI run [39056308692](https://github.com/kokoosabzi/sabt/actions/runs/39056308692): **136 tests passed**, plus fresh SQLite migration, Alembic head, downgrade and re-upgrade checks.
- **Integrated:** PR #4 (browser E2E) merged into PR #3; PR #3 (parser hardening) merged into PR #2; PR #2 (staged import) merged into PR #1.
- **Stable foundation milestone:** PR #1 merged into `main` as commit `083f6728adf3107c04535b05fe944f94b5b0b802` after the combined 136-test CI and SQLite migration round-trip passed.


## Jalali reporting-period controls — 2026-10-17
- [x] Replace Gregorian browser datetime-local inputs with explicit Jalali date and time fields in the Persian RTL reporting portal.
- [x] Accept Persian and Latin numerals, validate Jalali month/day combinations using the browser's Persian calendar data, and convert the selected date/time using the authorized project's timezone before sending UTC API bounds.
- [x] Initialize the seven-day report window and current time using the selected project's timezone and display timestamps using Persian locale formatting.
- [x] Add Playwright/Chromium browser coverage for invalid Jalali dates, Persian-digit input, and successful report loading with a Jalali date range.
- [x] Update the README to describe current date handling and separate implemented from planned export/event work.
- [x] Verified GitHub Actions run [39057009090](https://github.com/kokoosabzi/sabt/actions/runs/39057009090) on commit `1d7aa9dd922cd7914c6b5ca3b1494eafdde67dea`: **137 tests passed, 2 warnings**; Chromium browser E2E passed and fresh SQLite upgrade, Alembic head, downgrade, and re-upgrade all passed.


## Shared date/time picker standard — 2026-10-17
- [x] Replace manual Jalali date text entry with a read-only, keyboard-accessible calendar picker; dates are selected from valid Jalali calendar days only.
- [x] Replace free-entry time fields with hour/minute selection controls in 24-hour format; initialize from the selected project's timezone.
- [x] Use the browser's built-in Persian calendar data (Intl) without CDN or runtime network dependency, preserving offline/LAN compatibility.
- [x] Keep UTC storage/API timestamps and project-timezone conversion unchanged; add Chromium browser E2E coverage for picker-only date entry and hour/minute controls.
- [x] GitHub Actions run [39057857094](https://github.com/kokoosabzi/sabt/actions/runs/39057857094) passed on commit `b6152b0dc0a1c4aaedab877af0ac03e346b37627`: **137 tests passed, 2 warnings**; Chromium E2E and fresh SQLite upgrade, Alembic head, downgrade, and re-upgrade checks all passed.


## Excel report exports — 2026-10-17
- [x] Add permission-scoped Excel (.xlsx) export for management summary metrics, workflow operations, and persisted workflow events.
- [x] Reuse the same project authorization and report filters as the corresponding JSON/CSV endpoints; cap bulk exports at 5,000 rows.
- [x] Create right-to-left worksheets with Persian headers, freeze panes, filters, and bounded column widths.
- [x] Neutralize formula-like untrusted text cells and serialize structured event metadata safely.
- [x] Add API tests that reopen generated workbooks, validate Persian headers/content type, and verify project authorization.
- [x] GitHub Actions run [39058393067](https://github.com/kokoosabzi/sabt/actions/runs/39058393067) passed on commit `f36c746d6f2696171b39046a8942bdc104f0642d`: **142 tests passed, 2 warnings**; Chromium E2E and fresh SQLite upgrade, Alembic head, downgrade, and re-upgrade checks all passed. Excel timestamp columns are explicitly labeled UTC; PDF/print exports remain the next slice.


## PDF-ready report printing — 2026-10-17
- [x] Add print-ready RTL layouts for management summary, all filtered workflow rows, all filtered persisted-event rows, and contract transfer history.
- [x] Provide an explicit “Print / Save PDF” action in the print view; use the browser/Windows print engine so the user can choose “Save as PDF” without a server-side PDF dependency or internet access.
- [x] Keep dynamic report values in text nodes rather than injecting them as HTML; enforce project-scoped APIs and a 5,000-row limit for bulk print reports.
- [x] Add a Chromium E2E check for the RTL, PDF-ready management print view.
- [x] GitHub Actions run [39058723867](https://github.com/kokoosabzi/sabt/actions/runs/39058723867) passed on commit `1344fe479d6d973225b4c8d50b27773899a96301`: **143 tests passed, 2 warnings**; Chromium E2E and fresh SQLite upgrade, Alembic head, downgrade, and re-upgrade checks all passed.
- [x] Final merged `main` verification: [GitHub Actions run 39058901990](https://github.com/kokoosabzi/sabt/actions/runs/39058901990) passed **143 tests, 2 warnings** after PR #9 was merged.


## Project-isolation audit — 2026-10-20

- [x] Merged PR #40 after CI passed: inaccessible and nonexistent Parent Contract numbers now return the same HTTP status and response body; inactive-user authorization errors remain distinct. Merge commit: `cbf1fd5dace789c791e6e06ea6190c4027e5ad36`.
- [x] Reviewed project-scoped report queries: management summary, workflow operations, workflow events, and report project context authorize project access before returning data; report queries filter by project ID, and workflow-event queries also verify the linked operation belongs to that project.
- [x] Reviewed core project-scoped relations already protected by composite foreign keys: operations ↔ project operation type/property/parent contract; operation parties ↔ operation/project-person membership; operation appointments ↔ appointment/operation; snapshots ↔ operation/person/property/party; contracts ↔ operation/property; workflow events ↔ operation.
- [x] Found a remaining database-integrity gap in project-specific configuration: workflow, numbering, and contract-number policies could pair a project ID with an operation type configured only for another project.
- [x] Added migration 0017 and matching ORM composite foreign keys for `operation_type_workflows`, `numbering_policies`, and `contract_number_policies`; `NULL project_id` remains the global-configuration mode.
- [x] Migration 0017 checks for existing invalid scoped configuration rows and aborts with counts instead of silently changing them.
- [x] Added a database regression test proving all three policy tables reject cross-project operation-type references while global configuration rows remain valid.
- [x] Verified CI for migration 0017 and the full suite on commit `ce45e31d2bed627de42e26103256026977402df6`; GitHub Actions run [39485712728](https://github.com/kokoosabzi/sabt/actions/runs/39485712728) passed, including fresh SQLite upgrade, Alembic head, downgrade, and re-upgrade.
- [x] Focus-reviewed existing Operation service entry points: create and finalize authorize against the operation's project; operation-type activation, property/project association, parent-contract project, appointment project, and party membership are checked against that same project before writes/finalization.
- [x] Focus-reviewed Parent Contract service entry points: creation and project-code changes authorize against the supplied project; history lookup authorizes against the resolved Parent Contract's project and scopes linked Operations and owner/person membership to that project.
- [x] Focus-reviewed report service entry points: report project context authorizes before returning project data; management/workflow/event queries filter by project, and event reports also constrain the linked Operation to the same project.
- [x] Merged PR #41 by squash after CI run [39485712728](https://github.com/kokoosabzi/sabt/actions/runs/39485712728) passed on code commit `ce45e31d2bed627de42e26103256026977402df6`. Merge commit: `88f062f3cab2f1bc293707e2298f36dc3db79d1a`.
- [x] Confirmed the current app entrypoint mounts contracts, contract import, and reports routes; no policy-configuration mutation router is mounted in `app/main.py`. Operation services are currently reviewed at service level, but are not mounted as an API router in that entrypoint.
- [ ] Continue the broader Phase 0 service/resource authorization audit and add route-level authorization tests whenever policy/configuration mutation endpoints are introduced. The focused review above is not proof that every service is covered; database constraints do not replace service authorization.
- [ ] Verify post-merge CI on `main` for merge commit `88f062f3cab2f1bc293707e2298f36dc3db79d1a`; the available workflow lookup has not returned a post-merge run yet.

## Operation lifecycle audit — 2026-10-20

- [x] Compared `app/operations/service.py::finalize_operation` with `WORKFLOWS.md` and `DOMAIN_MODEL.md`.
- [x] Found a concrete lifecycle gap: finalization currently rejects already-finalized operations and stale versions, but does not enforce the documented transition path `Draft → In Progress → Ready for Finalization → Finalized`. Existing tests intentionally finalize drafts directly, so adding a simple status guard alone would break established test fixtures and transfer-finalization tests.
- [x] Implemented on PR #42: permission-checked workflow transitions, optimistic-version checks, persisted workflow events, configured ready-for-finalization guard, and regression coverage for skipped/stale transitions and transfer/finalization side effects. CI run [39487383294](https://github.com/kokoosabzi/sabt/actions/runs/39487383294) passed on the prior code revision; a later review added rejection of duplicate workflow sequence numbers, so the latest head still requires CI.
- [x] Implemented the focused lifecycle change on branch `feature/operation-workflow-transitions`; PR #42 adds the transition service and enforces the ready-for-finalization guard. Full CI passed on the final branch head in run [39488009480](https://github.com/kokoosabzi/sabt/actions/runs/39488009480), including browser tests and SQLite migration round-trip.


## Operation workflow transition implementation — 2026-10-20

- [x] Added a service-level `transition_operation` function on focused branch `feature/operation-workflow-transitions`. It requires project-scoped `operation.edit`, checks optimistic version, rejects transitions from finalized operations, uses active project-specific workflow states (falling back to global states only when no project-specific states exist), allows only the next configured `sequence_no`, and records a workflow event.
- [x] Added focused service tests for rejecting skipped transitions, successful state/event/version updates, missing configuration, and stale versions.
- [x] Reviewed the branch diff against the workflow model and service tests; found and fixed an ambiguity where duplicate `sequence_no` values could make the next configured state depend on row ID.
- [x] CI run [39488009480](https://github.com/kokoosabzi/sabt/actions/runs/39488009480) passed on the updated head: browser tests, full test suite, fresh SQLite upgrade, Alembic head verification, and downgrade/re-upgrade.
- [x] Follow-up completed in the same PR: finalization now requires the configured `READY_FOR_FINALIZATION` state, and finalization/transfer tests advance through configured states before finalizing.


## Finalization readiness enforcement — 2026-10-20

- [x] `finalize_operation` now rejects operations unless `current_workflow_state == READY_FOR_FINALIZATION` and the active workflow configuration contains that state.
- [x] Project-specific workflow configuration takes precedence; global workflow configuration is used only when no active project-specific workflow is configured.
- [x] Existing successful/negative finalization and transfer tests were adjusted to use the transition service instead of bypassing the lifecycle.
- [x] Added a regression test proving a DRAFT operation cannot be finalized directly.
- [x] Initial CI run [39487122804](https://github.com/kokoosabzi/sabt/actions/runs/39487122804) found two stale assertions expecting DRAFT after advancing operations to READY_FOR_FINALIZATION. The assertions were corrected; subsequent CI run [39487383294](https://github.com/kokoosabzi/sabt/actions/runs/39487383294) passed on the prior revision; final-head CI run [39488009480](https://github.com/kokoosabzi/sabt/actions/runs/39488009480) also passed after adding duplicate-sequence validation and its regression test.


## Excel Parent Contract import leading-zero handling — 2026-10-20

- [x] Audited the existing CSV/XLSX import path before extending it; parsing and preview are side-effect free, duplicate detection is present, confirmation revalidates submitted rows, and API tests cover rollback on later-row failure and a duplicate appearing after preview.
- [x] Found an Excel usability edge case: numeric suffix cells formatted as `0000` display leading zeroes in Excel, but parsing only saw the underlying numeric value and rejected it.
- [x] Added support for preserving leading zeroes only when the XLSX suffix cell explicitly uses the four-zero number format. Plain numeric/general cells are not guessed or silently rewritten.
- [x] Added parsing tests for formatted numeric cells and unformatted numeric cells.
- [x] CI run [39488513533](https://github.com/kokoosabzi/sabt/actions/runs/39488513533) passed on this PR head: full pytest suite, Chromium browser E2E coverage, fresh SQLite upgrade, Alembic head verification, and downgrade/re-upgrade checks.

## Import endpoint authorization regression coverage — 2026-10-20

- [x] Security review confirmed that import preview, edited-row validation, and confirmation all flow through project-scoped `parent_contract.create` authorization before returning preview data or writing contracts.
- [x] Added explicit negative API regression tests for `/validate` and `/confirm` when project create permission is absent; both assert HTTP 403 and no contract writes.
- [x] CI run [39489204971](https://github.com/kokoosabzi/sabt/actions/runs/39489204971) passed on this test head: full test suite, Chromium browser E2E, fresh SQLite upgrade, Alembic head verification, and downgrade/re-upgrade checks.

## Report export authorization audit — 2026-10-20

- [x] Reviewed management summary, workflow report, workflow event report, and export routes; report services authorize project scope before querying report data.
- [x] Added negative API regression coverage for management-summary XLSX, workflow-events XLSX, and workflow-events CSV exports when project access is revoked; each must return HTTP 403.
- [x] PR [#45](https://github.com/kokoosabzi/sabt/pull/45) merged as `fe64f420b6fd587badddac432e17cea36f06ce41` after CI run [39489639488](https://github.com/kokoosabzi/sabt/actions/runs/39489639488) passed on the exact PR head: full pytest suite, Chromium browser E2E, fresh SQLite upgrade, Alembic head verification, and downgrade/re-upgrade checks.
- [x] Post-merge CI run [39489788033](https://github.com/kokoosabzi/sabt/actions/runs/39489788033) passed on `main` (`fe64f420b6fd587badddac432e17cea36f06ce41`): full test suite, Chromium browser E2E, fresh SQLite upgrade, Alembic head verification, and downgrade/re-upgrade checks.
