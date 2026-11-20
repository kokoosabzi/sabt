# SABT

SABT is a Persian-first local/LAN document and operation management system for real-estate registration workflows.

## Architecture baseline

The repository combines architecture-first specifications with a working FastAPI foundation, authorized contract-history/report APIs, and an initial Persian RTL reporting portal. The portal is served by the application at `/portal/`; the feature set is still under development and must not be treated as a complete production UI.

Core documents:
- [ARCHITECTURE.md](ARCHITECTURE.md)
- [DOMAIN_MODEL.md](DOMAIN_MODEL.md)
- [WORKFLOWS.md](WORKFLOWS.md)
- [OPEN_DECISIONS.md](OPEN_DECISIONS.md)

## Development guide

- [SKILL.md](SKILL.md) — coding-agent rules and implementation invariants
- [AGENTS.md](AGENTS.md) — entry instructions for Codex and other agents
- [AI_AGENT_INSTRUCTIONS.md](AI_AGENT_INSTRUCTIONS.md) — detailed execution contract
- [PROGRESS.md](PROGRESS.md) — phased roadmap, verified status, and next tasks

Before implementing a feature, read the development guide and update `PROGRESS.md` with actual verification results. `PROGRESS.md` is the current execution ledger; older dated entries are historical and may be superseded by later verified entries.

## Current development status
This development branch adds authenticated project onboarding, manual Parent Contract creation, staged CSV/XLSX import, operation creation/party/workflow/finalization APIs, transactional transfer child numbering, authorized current-owner history, Jalali reporting, CSV/Excel exports, browser print views, and Windows setup/backup/restore launchers. It is still an early MVP/API slice rather than a complete production UI. Full person/property administration screens, end-user operation forms, broader workflow-event coverage, restrictions, managed documents, appointments/reminders, templates/PDF generation, and release packaging remain future work. See `PROGRESS.md` for the verified state and next task.

## Core rule
SABT does not process money. Financial activity occurs outside the system; related receipts or scans may be stored as operation documents.


## Reporting portal (early implementation)
- Start the FastAPI application using the repository's normal ASGI command, then open `/portal/` on the same host.
- Sign in with an existing SABT user. The portal uses the current bearer-session API; it does not create or bypass authorization.
- Available first-pass pages: management summary, paginated workflow report, persisted workflow events, and Parent Contract transfer history.
- Report access requires the corresponding project-scoped permissions. Enter the numeric Project ID to request a report.
- The reporting period uses a keyboard-accessible Jalali calendar picker and controlled 24-hour hour/minute selectors; users do not type date/time strings manually. The picker uses the browser's built-in Persian calendar data (Intl) and works offline without a third-party CDN. Selected date/time is converted using the authorized project's timezone before UTC timestamps are sent to the API. Report timestamps are displayed in the project timezone with Persian locale formatting. Management summary, workflow, and persisted-event reports provide permission-scoped CSV and Excel exports; these pages and contract history also provide print-ready reports that can be saved as PDF through the browser's print dialog. Excel timestamp columns are explicitly labeled UTC.

## Windows local MVP preview

The current development branch includes preliminary Windows launchers:
- Run `setup.bat` once to create the Python 3.12 virtual environment, install dependencies, apply migrations, and create the first administrator on a fresh database.
- Run `start.bat` for the local server and portal.
- Run `stop.bat` to stop the verified SABT server process.
- The Windows CI smoke also creates a Parent Contract, finalizes a transfer with an approved Buyer / Transferee, verifies the `/<sequence>` child number and current-owner history, then backs up, mutates, restores, restarts, and verifies the original transfer chain.

See [HELP/WINDOWS_INSTALL.md](HELP/WINDOWS_INSTALL.md) and [HELP/ADMIN_BOOTSTRAP.md](HELP/ADMIN_BOOTSTRAP.md) for setup details and data-location safety. The server currently binds only to `127.0.0.1:8000`. SQLite backup and offline restore commands are available through `python -m app.backup`; encrypted backups, retention policy, LAN access, password recovery, and a standalone MSI/EXE installer are not yet delivered. The current branch's Windows CI verifies the API transfer flow, but the full person/property/operation entry UI and manual acceptance on the user's own Windows PC are not yet complete.
