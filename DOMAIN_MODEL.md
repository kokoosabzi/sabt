# SABT — Domain Model

Version: 0.1

## Entity map
Project -> Appointments, Operations, enabled Operation Types, Parent Contracts
Person -> reusable master data; referenced by Operation Parties
Property -> reusable master data; project association/context is separate; referenced by Contracts
Appointment -> 0..N Operations
Parent Contract -> 0..N transfer Operations (stable transfer-chain root)\nOperation -> 0..1 transaction-specific Contract, 0..1 Parent Contract, N Parties, 1 Property context, N Documents, N Custom Field values, N Audit events
Contract -> exactly 1 Property and manual Contract Number

## Project
A lightweight organizational/business context with identity, status, branding references and basic settings. Specialized configuration belongs to dedicated configuration entities.

## Person
Central reusable record. Core structured fields may include first name, last name, father name, national ID, mobile, address and notes. Additional custom fields are supported.

## Property
Central reusable record. Core fields include project, block/tower, floor, orientation, unit number/code, plaque/parcel number, address and notes. Additional custom fields are supported. Every Contract has exactly one Property.

## Appointment
Independent from Operation. It contains project, appointment type, date/time, parties/customer references, status and notes. Statuses include Free, Reserved, Present, No-Show, Cancelled and Done. Appointment Type controls the action caused by Present. One Appointment may link to multiple Operations.

## Operation
Primary workflow entity. It contains project, operation type, optional appointment, status, parties, property context, optional Contract, documents, custom fields, workflow state, timestamps and concurrency version. It may exist without an Appointment or Contract.

## Operation Type
Global base configuration activated and configured per Project. It can define fields, custom fields, documents, workflow, print templates, appointment behavior, numbering and validation rules.

## Operation Parties
Dynamic role-based membership. Each party links an Operation to a Person and a configurable role. The system may ship with common examples such as Buyer, Seller, Attorney and Representative, but roles are not hard-coded as the complete set.

## Snapshots
Working snapshots are captured at operation creation. An immutable final snapshot is created at Finalize. Finalized historical records remain stable if master Person or Property data changes later.

## Contract
Optional business record of an Operation, maximum one per Operation. Contract Number is manually entered. Registration Number is system-generated under configurable policy. Contract references exactly one Property and can have multiple parties.

## Document
Metadata is stored in SQLite and file bytes on filesystem. Metadata includes document type, title, original filename, storage key, MIME type, size, hash, number/date where applicable, description, archive state, creator and timestamps. Replacing a file supersedes the previous file rather than creating document file versions; the replacement is audited.

## Custom Fields
Metadata-driven field definitions and values. Definitions include key, label, data type, required flag, validation, order, active state and scope. Values are stored separately.

## Audit
Captures actor, action, entity, timestamp, reason where required and structured before/after data where practical. Sensitive actions always create audit records.

## Restrictions
V1 restrictions are Contract-oriented. Rules can match contract numbers and define severity, action, message, override permission, effective dates and import source. CSV, Excel and clipboard import are supported with validation and preview.

## Registration Number
Generated business identifier with Admin-configurable scope, prefix, sequence, formatting, reset policy and collision handling. Internal DB ID remains independent.


## V1 Frozen Decisions

### Person and Property scope
Person and Property are central master records and are not owned by a single Project. Project-specific visibility/context is represented through explicit project association/access structures.

### Operation Type configuration
Global base definitions are separated from Project activation/configuration. Critical behavior such as workflow, numbering, required documents and permissions is represented explicitly rather than relying only on opaque configuration JSON.

### Party roles
Party roles are dynamic. Multiple people may occupy the same role. Operation Type configuration defines required roles and cardinality. Used roles are retired/deactivated rather than deleted.

### Numbering
Registration numbers are allocated transactionally from explicit numbering policy/state and never through MAX()+1. Allocation occurs at successful finalization when the operation type requires it.

### Contract numbers
Contract-number uniqueness is an explicit policy: GLOBAL, PROJECT, OPERATION_TYPE, or NONE. The policy is enforced transactionally and is not represented by one unconditional database UNIQUE constraint.

### Snapshots
The immutable final business truth is the finalized OperationVersion snapshot. It includes the operation core, parties and role assignments, property context, contract data when present, relevant custom-field values, workflow state, business identifiers, and references to the exact template/branding inputs required for reproducibility.

### Project roles
Users may have global roles and project-scoped roles. Project access is separate from role assignment and is required for project-scoped actions.


## Parent/child model — proposed architecture direction

- Parent Contract is a separate entity from the existing optional transaction-specific Contract record.
- Transfer Operations reference the Parent Contract; do not encode the chain by reusing OperationVersion rows or by assuming the optional Contract relationship is sufficient.
- The UI should show a parent summary and chronologically/sequence-ordered transfer tree. Selecting a child opens its own operation details and immutable finalized snapshot.
- The parent detail view may show a current-owner summary derived from the latest valid finalized transfer, while preserving the initial owner on the Parent Contract.
- Bulk import of existing parent contracts and member/owner rows is a staged, auditable import workflow, not direct unvalidated inserts.
- Project codes are exactly two digits and begin at `10`; `01`–`09` are invalid. The code is shared by all members/contracts within a Project and stored as text. A Parent Contract number is six digits: Project code plus a four-digit member/contract suffix. The suffix may be entered manually or imported from Excel/CSV, optionally alongside unit/property details. Global uniqueness/immutability of Project codes, child-number gap policy, and ownership-effective status remain open.


## Confirmed Parent Contract ownership rule — 2026-10-14

- The OperationParty role that receives ownership on a transfer is **Buyer / Transferee**, with canonical technical code `BUYER_TRANSFEREE`.
- A transfer linked to a Parent Contract cannot be finalized without at least one active Buyer / Transferee party.
- Current owner is derived from the latest valid finalized transfer: the Operation must be finalized, have its current finalized OperationVersion, have a child transfer number, and include Buyer / Transferee party membership.
- Draft and non-finalized operations never change current ownership. If no valid finalized transfer exists, current owner is the Parent Contract initial person.
- Multiple Buyer / Transferee parties are supported and returned as a list to avoid silently discarding joint transferees.
