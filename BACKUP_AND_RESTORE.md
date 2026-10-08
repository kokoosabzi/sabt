# BACKUP_AND_RESTORE.md

## 1. Purpose

This document defines the V1 backup, restore, integrity, retention, rotation, scheduling, storage, validation, and audit architecture.

The backup system must produce a restorable snapshot of the SABT installation, not merely a copy of the SQLite database.

Selected V1 requirements:

- manual backup
- automatic backup
- configurable rotation
- full restorable snapshot
- Admin-only restore

## 2. Core Principles

1. A backup is a restorable system snapshot.
2. SQLite alone is not a complete backup.
3. Database and managed files must be captured consistently.
4. Backup creation must not report a falsely successful partial backup.
5. Every backup must have integrity metadata.
6. Restore is a privileged destructive operation.
7. A pre-restore backup is mandatory.
8. Restore validates the backup before modifying live state.
9. Restore validates the system again after restoration.
10. Backup and restore operations are audited.
11. Backup files contain sensitive business data and require access control.
12. Rotation must never delete the only known valid backup.
13. Backup logic should remain compatible with future PostgreSQL migration where practical.
14. Ordinary backups should coexist with normal business use where the underlying snapshot mechanism permits.

## 3. Full Backup Contents

A V1 full backup should contain:

### Database

- SQLite database
- migration/schema state
- configuration stored in database
- users, roles, permissions
- Projects
- People
- Properties
- Appointments
- Operations
- Contracts
- Document metadata
- Custom fields
- Restrictions
- Templates and template revisions
- Generated-document metadata
- Audit records
- Reminder definitions/events
- Numbering policies
- Branding metadata
- System settings

### Managed files

- uploaded documents
- generated PDFs
- print-template assets
- branding assets
- managed fonts when they are part of the installation
- other application-managed files required for restoration

### Manifest

Every backup must contain a manifest describing:

- backup ID
- backup format version
- application version
- schema/migration version
- creation timestamp
- included components
- file count
- total byte count
- checksums
- completion status

Deployment secrets should not automatically be included in plaintext.

## 4. Backup Format

Recommended logical structure:

backup/
- manifest.json
- database/
  - sabt.db
- storage/
  - documents/
  - generated/
  - templates/
  - branding/
- metadata/
- checksums/

The final package may be a single archive with an application-specific extension such as .sabtbackup.

The archive format must be versioned and documented.

It must not depend on absolute machine-specific paths.

## 5. Backup Manifest

The manifest is the authoritative description of backup contents.

Suggested fields:

- format_version
- backup_id
- created_at
- application_version
- schema_version
- database_filename
- database_size
- database_sha256
- included_storage_roots
- file_count
- total_size
- manifest_hash
- completion_status
- backup_type
- source_instance_id where needed

For each managed file:

- relative path/storage key
- size
- SHA-256
- MIME type where available

Only relative/internal storage keys are permitted.

## 6. Backup Types

V1 supports:

### Full Manual Backup

Explicitly requested by an authorized user.

### Full Automatic Backup

Executed by the configured scheduler.

### Pre-Restore Backup

Automatically created immediately before restore.

### Optional Safety Backup

May be introduced before other high-risk system changes.

V1 uses full backups only. Incremental/differential backup is not required.

## 7. Manual Backup Flow

1. authenticate
2. authorize backup.create
3. resolve backup destination
4. acquire backup coordination lock if required
5. create consistent database snapshot
6. collect managed files
7. calculate hashes/metadata
8. create manifest
9. package archive
10. validate archive
11. atomically publish final backup
12. update backup metadata
13. apply rotation
14. audit result

Any critical failure produces a failed backup, never a successful partial backup.

## 8. Automatic Backup

Configuration should include:

- enabled/disabled
- schedule
- destination
- retention count
- minimum free-space requirement
- retry enabled/disabled
- maximum retry count
- optional execution window

The scheduler belongs to the backend/server process rather than the browser.

If the server is not running at the scheduled time, a missed-run policy must be applied.

Recommended V1 behavior:

- record the missed schedule
- optionally run once after server startup if configured
- never silently treat a missed run as successful

## 9. Backup Destination

V1 should support:

- local backup directory

Architecture should permit future:

- network share
- external drive
- encrypted remote storage
- cloud/object storage

The backup destination should not be the same physical directory as live application storage by default.

The system should warn about dangerous source/destination overlap.

## 10. Backup Naming

Use machine-safe sortable names.

Conceptual example:

sabt-full-YYYYMMDD-HHMMSS-{backup_id}.sabtbackup

Never use user-entered names directly as filesystem paths.

## 11. Consistent SQLite Snapshot

Do not blindly copy the live database while writes are occurring.

Use a SQLite-safe consistent snapshot mechanism, preferably:

- SQLite Online Backup API
- or another SQLite-supported consistent snapshot mechanism

The resulting database snapshot must be independently openable and valid.

WAL-related state must be captured consistently by the selected SQLite backup method.

## 12. Filesystem Consistency

Database metadata and filesystem files form one logical backup, although SQLite and the filesystem do not provide a single distributed transaction.

Recommended approach:

1. create database snapshot
2. capture managed file inventory
3. copy/hash files
4. detect changes during capture where possible
5. retry changed files when safe
6. reconcile inventory against the database snapshot
7. mark backup invalid if required consistency cannot be established

For sensitive deployments, a short application-level write pause may be introduced during final reconciliation.

Correctness takes priority over throughput.

## 13. File Hashing

Managed files use SHA-256 or equivalent strong hashing.

Each file record contains:

- relative storage key
- size
- hash

Hashing supports integrity checking, corruption detection, restore verification, and reproducibility.

## 14. Backup Validation

A backup is validated before being marked successful.

### Archive

- readable
- expected manifest exists
- format version supported

### Database

- extractable
- SQLite can open it
- schema/migration state is coherent
- required tables exist
- foreign-key checks can run

### Files

- expected file count matches manifest
- sizes match
- hashes match
- required storage roots exist

### Metadata

- manifest is internally consistent
- backup ID exists
- creation time is valid
- application/schema versions are recorded

A failed validation means the backup is not a valid restore point.

## 15. Backup Metadata

Reserve a database entity named backups.

Suggested fields:

- id
- backup_id
- backup_type
- path/storage_key
- format_version
- application_version
- schema_version
- created_at
- completed_at
- size_bytes
- file_count
- sha256
- status
- validation_status
- error_code
- error_message
- created_by
- retention_class
- version

The live database is not the only source of truth. The archive remains self-describing through its manifest.

## 16. Atomic Publication

Never expose a partially written archive as a valid backup.

Recommended:

1. write temporary archive
2. flush and close
3. validate
4. calculate final archive hash
5. atomically rename/move to final name
6. update metadata
7. audit

Crash before publication leaves a temporary artifact that can be cleaned later.

## 17. Rotation

Rotation is configurable.

Recommended parameters:

- minimum backups to retain
- maximum backups
- maximum age
- separate retention for manual backups
- separate retention for pre-restore backups
- minimum number of validated restore points

Deletion occurs only after a replacement backup is successfully created and validated.

## 18. Rotation Safety

Rules:

1. never delete a backup currently being created
2. never delete the newest validated backup merely because it is old
3. never reduce validated restore points below configured minimum
4. never delete the only known valid backup
5. failed backups do not count as restore points
6. pre-restore backups receive elevated retention
7. rotation actions are audited

Recommended default behavior:

Keep the newest N validated full backups while preserving at least one safety backup according to policy.

## 19. Backup Failure Handling

Possible states:

- Requested
- Running
- Validating
- Completed
- Failed
- Corrupt/Invalid
- Retained
- Deleted

Automatic retries must be bounded.

Failures identify stage, error code, safe technical message, and timestamp.

## 20. Free-Space Protection

Before backup:

- inspect available destination space
- estimate required space
- compare with configured minimum
- warn or abort if insufficient

During backup:

- detect write failures
- mark backup failed
- never mark a partial archive successful

## 21. Restore Philosophy

Restore replaces the current application state with a captured state.

Therefore:

- Admin-only by default
- explicit confirmation
- pre-restore backup mandatory
- source validation mandatory
- controlled restore process
- post-restore validation mandatory
- restore audit mandatory

The destructive nature must be obvious to the administrator.

## 22. Restore Flow

1. authenticate Admin
2. authorize backup.restore
3. select backup
4. validate backup
5. display backup metadata
6. display source application/schema version
7. display restore scope
8. require explicit confirmation
9. create pre-restore backup
10. verify pre-restore backup
11. enter restore-safe/maintenance state
12. restore database snapshot
13. restore managed files
14. validate database/files
15. validate application invariants
16. reload/restart application state if required
17. record restore audit
18. return system to normal state

If restore fails, use the defined rollback/recovery path.

## 23. Pre-Restore Backup

A pre-restore backup is mandatory by default.

It protects against:

- wrong backup selection
- source corruption discovered late
- schema mismatch
- operator error
- incomplete restore
- application incompatibility

Pre-restore backups receive elevated retention and are not immediately removed by ordinary rotation.

## 24. Restore Validation Before Modification

Before changing live state, validate:

- archive integrity
- manifest
- database readability
- schema/migration compatibility
- required storage roots
- file hashes
- backup format
- application compatibility

If compatibility is uncertain, restore stops before destructive steps.

## 25. Restore Compatibility

Possible source states:

### Same or supported older version

Restore allowed after validation and supported migration.

### Newer unsupported version

Restore blocked.

### Unknown format/schema

Restore blocked.

The system must never silently downgrade schema.

## 26. Database Restore

Restore must:

- stop or isolate writes
- replace the database safely
- preserve required filesystem permissions
- re-establish required SQLite settings
- run integrity checks
- run foreign-key checks
- verify migration state

Preferred strategy:

1. restore into a temporary database
2. validate it
3. switch active database reference atomically

This is safer than immediately destroying the active database.

## 27. File Restore

Managed files are restored only under the configured storage root.

Reject:

- absolute archive paths
- path traversal
- unsafe archive entries

After extraction:

- verify hashes
- validate expected inventory
- apply required permissions

An archive must never write outside the configured application storage root.

## 28. Restore and Secrets

A business backup should not automatically contain plaintext:

- session secrets
- password-recovery secrets
- QR signing private keys
- external-service credentials

Recommended V1 policy:

- business data and managed files are backed up
- deployment secrets remain installation-specific
- restore checks whether required local secrets are available
- missing required secrets produce a controlled post-restore configuration task

Encrypted secret backup is a separate future design.

## 29. Restore and User Accounts

Restoring the database also restores the user/role state in that backup.

Therefore the administrator must understand that current user configuration may be replaced.

Post-restore login behavior must be communicated clearly.

An emergency admin recovery workflow should be designed if restored credentials cannot authenticate the operator.

## 30. Restore and Application Version

Record:

- source application version
- current application version
- source schema version
- resulting schema version
- migration actions if any

Do not silently mix incompatible application binaries and database state.

## 31. Restore Rollback and Recovery

Preferred strategy:

1. preserve the pre-restore backup
2. validate restored temporary state before activation
3. switch active state only after validation
4. if post-switch validation fails, stop normal operation
5. recover using pre-restore backup
6. audit failure and recovery

The system should fail closed rather than continue with partially restored state.

## 32. Maintenance and Restore Lock

While restore runs:

- normal business writes are blocked
- concurrent restore attempts are blocked
- backup jobs are paused
- scheduled mutating jobs are paused
- users see maintenance/restore status where appropriate

Read access may also be blocked during the critical replacement phase.

The restore lock is server-side, not merely a UI flag.

## 33. Backup Concurrency

Backup and ordinary business writes may coexist if the SQLite snapshot method guarantees consistency.

However:

- restore blocks normal writes
- restore blocks concurrent backup
- only one restore runs at a time
- rotation cannot delete an archive currently used for restore
- automatic backup detects restore mode and defers

## 34. Automatic Backup Scheduler

Scheduler state should include:

- persistent configuration
- next-run timestamp
- last-run timestamp
- last-success timestamp
- last-failure timestamp
- retry state
- missed-run handling
- audit/logging

The scheduler is owned by the backend process.

Future Windows-service integration should not change the scheduler contract.

## 35. Backup Health

The application should expose:

- last successful backup
- last failed backup
- next scheduled backup
- backup destination
- valid backup count
- destination free space
- validation status

Critical failures should create an in-app notification.

External email/SMS is not required for V1.

## 36. Permissions

Suggested permissions:

- backup.view
- backup.create
- backup.configure
- backup.restore
- backup.delete

Recommended defaults:

- backup.restore: Admin-only
- backup.configure: privileged administrator
- backup.delete: privileged administrator
- backup.create: authorized administrative role
- backup.view: authorized administrative role

Admin actions remain audited.

## 37. Audit

Audit at minimum:

- manual backup requested
- automatic backup started/completed/failed
- backup validation
- rotation/deletion
- backup configuration changes
- restore requested
- restore validation
- pre-restore backup
- restore started/completed/failed
- recovery/rollback
- maintenance/restore mode transitions

Include:

- actor where applicable
- timestamp
- backup ID
- backup type
- safe storage reference
- result
- error code
- application/schema versions
- reason where required

Never record secrets.

## 38. Backup Security

Backup archives are sensitive data.

At minimum:

- restrict filesystem permissions
- prevent normal users from browsing backup directories
- use internal backup IDs
- do not expose raw paths in UI
- validate archive contents before restore
- prevent path traversal
- avoid secrets in backups
- consider encryption as a future security enhancement

## 39. Backup Integrity

Integrity is checked at two levels.

### Archive-level

Hash the complete backup archive.

### Content-level

Hash each managed file and the database snapshot.

This provides both overall integrity and precise corruption diagnosis.

## 40. Disaster-Recovery Check

A backup is useful only if it can restore.

The architecture should support periodic isolated restore testing:

- select backup
- restore into isolated temporary environment
- validate schema/files
- run application health checks
- report result
- never modify live installation

This may become a scheduled feature after V1.

## 41. Retention Policy

Retention is configurable by:

- count
- age
- backup type
- minimum valid backups

Conceptual classes:

- automatic
- manual
- pre-restore

Pre-restore backups have stronger retention than ordinary automatic backups.

Retention must not override future legal/business preservation requirements.

## 42. Storage Layout

Recommended:

backups/
- active/
- temp/
- failed/
- archive/

Only validated completed backups belong in the active restore-point area.

Temporary and failed files may be cleaned according to policy.

## 43. Database Alignment

Reserve a backups entity.

Suggested fields:

- id
- backup_id
- backup_type
- status
- validation_status
- storage_key
- format_version
- application_version
- schema_version
- size_bytes
- file_count
- sha256
- created_at
- completed_at
- created_by
- error_code
- error_message
- retention_class
- version

An optional backup_runs entity may be added later for scheduler execution history.

## 44. API Boundary

Conceptual endpoints:

- GET /backups
- GET /backups/{id}
- POST /backups
- POST /backups/{id}/validate
- POST /backups/{id}/restore
- DELETE /backups/{id}
- GET /backup-settings
- PUT /backup-settings

Exact route names may change. All operations remain server-side and permission-protected.

## 45. Backup State Machine

Recommended:

Requested -> Running -> Validating -> Completed

Failure branches:

Running -> Failed
Validating -> Invalid

Retention:

Completed -> Retained
Retained -> Deleted

Restore:

Completed -> Restore Validating -> Restore Running -> Restored

Failure:

Restore Running -> Restore Failed

A failed restore must never be represented as successful restoration.

## 46. Acceptance Criteria

V1 backup/restore is acceptable when:

- manual full backup works
- automatic full backup works
- backup contains SQLite plus all required managed files
- backup has a self-describing manifest
- backup is validated before success
- archive and content hashes are recorded
- rotation is configurable
- rotation never removes the only valid restore point
- free space is checked
- restore is Admin-only
- restore validates the source before modification
- pre-restore backup is mandatory
- restore blocks concurrent business writes
- restored database and files are validated
- archive path traversal is impossible
- failed restore has a recovery path
- restore and backup actions are audited
- backup files are access-controlled
- deployment secrets are not silently embedded in plaintext
- application/schema compatibility is checked
- SQLite uses a consistent snapshot mechanism
- partial backups are never reported as successful

## 47. Open Decisions

1. Exact SQLite backup implementation/API.
2. Exact archive format and compression.
3. Backup encryption in V1 or later.
4. Exact scheduler implementation.
5. Missed automatic-backup policy.
6. Default retention count/age.
7. Exact secret-management mechanism for local Windows deployment.
8. Emergency admin recovery after restore.
9. Automatic migration of older backups.
10. Isolated restore testing in V1.
11. Exact backup deletion permission.
12. Network/external-drive backup support timing.

These decisions must not weaken the full-snapshot, validation-first, pre-restore-backup, Admin-only restore, integrity, and audit guarantees.
