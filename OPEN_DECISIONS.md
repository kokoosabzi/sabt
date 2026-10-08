# SABT — Remaining Design Decisions

Version: 0.1

These points remain intentionally open and must be decided before database schema is frozen.

1. Contract lifecycle: creation, detachment and correction relationship with Operation.
2. Registration number scope, prefix, sequence width, reset behavior and allocation rules.
3. Contract-number uniqueness policy and its allowed scopes.
4. Which Operation Type properties can be overridden per Project.
5. Party-role governance, including required roles and whether duplicate roles are allowed.
6. Complete permission matrix.
7. Exact immutable snapshot field sets for Person, Property, Party and Operation.
8. Atomic numbering behavior under concurrent users.
9. Storage retention for temporary files, generated PDFs, archived documents, physical deletions and backups.
10. Reminder delivery mechanism in V1; in-app notifications are sufficient unless external channels are later requested.
11. Timezone policy for backend timestamps and local presentation.
12. Search fields, filters and ranking.
