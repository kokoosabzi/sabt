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

Before implementing a feature, read the development guide and update `PROGRESS.md` with actual verification results.

## Core rule
SABT does not process money. Financial activity occurs outside the system; related receipts or scans may be stored as operation documents.


## Reporting portal (early implementation)
- Start the FastAPI application using the repository's normal ASGI command, then open `/portal/` on the same host.
- Sign in with an existing SABT user. The portal uses the current bearer-session API; it does not create or bypass authorization.
- Available first-pass pages: management summary, paginated workflow report, persisted workflow events, and Parent Contract transfer history.
- Report access requires the corresponding project-scoped permissions. Enter the numeric Project ID to request a report.
- The reporting period uses a keyboard-accessible Jalali calendar picker and controlled 24-hour hour/minute selectors; users do not type date/time strings manually. The picker uses the browser's built-in Persian calendar data (Intl) and works offline without a third-party CDN. Selected date/time is converted using the authorized project's timezone before UTC timestamps are sent to the API. Report timestamps are displayed in the project timezone with Persian locale formatting. Management summary, workflow, and persisted-event reports provide permission-scoped CSV and Excel exports. Excel timestamp columns are explicitly labeled UTC; PDF/print exports and broader workflow-event coverage remain planned.
