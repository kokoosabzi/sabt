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
- The reporting period uses explicit Jalali (Solar Hijri) date fields and time fields. Date input accepts Persian or Latin digits and is converted to the project timezone before UTC timestamps are sent to the API. Report timestamps are displayed in the project timezone with Persian locale formatting. Workflow and event reports support permission-scoped CSV export; Playwright/Chromium browser end-to-end coverage includes staged contract import. Excel/PDF report exports and broader workflow-event coverage remain planned.
