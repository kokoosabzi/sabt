# Agent Instructions — SABT

Before any non-trivial task, read these files in order:

1. `SKILL.md` — working rules, invariants, testing contract, and definition of done.
2. `PROGRESS.md` — active phase, verified status, known risks, and next task.
3. `AI_AGENT_INSTRUCTIONS.md` — detailed project execution contract.
4. Relevant architecture/domain documents listed in `AI_AGENT_INSTRUCTIONS.md`.

Do not add features that bypass the current phase's stabilization requirements. Inspect existing code and migrations before editing. Every meaningful change needs tests and an update to PROGRESS.md. Report exact commands and real results; never claim a test passed unless it ran. For substantial changes, use a focused PR and review its diff and CI results. Once required checks are green, migrations pass where relevant, and no blocking findings remain, merge the stable change promptly in accordance with the user's explicit instruction; do not leave stable PRs open by default. Never merge a failing or unverified change.

If a decision is unresolved or documents conflict, record the issue and ask rather than silently inventing a rule.
