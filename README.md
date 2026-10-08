# SABT

SABT is a Persian-first local/LAN document and operation management system for real-estate registration workflows.

## Architecture baseline

The current repository begins with an architecture-first specification. No application code is being generated until the domain model and workflows are sufficiently stable.

Core documents:
- [ARCHITECTURE.md](ARCHITECTURE.md)
- [DOMAIN_MODEL.md](DOMAIN_MODEL.md)
- [WORKFLOWS.md](WORKFLOWS.md)
- [OPEN_DECISIONS.md](OPEN_DECISIONS.md)

## Core rule
SABT does not process money. Financial activity occurs outside the system; related receipts or scans may be stored as operation documents.
