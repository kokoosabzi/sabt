# SABT

SABT is a Persian-first local/LAN document and operation management system for real-estate registration workflows.

## Architecture baseline

The current repository begins with an architecture-first specification. No application code is being generated until the domain model and workflows are sufficiently stable.

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
