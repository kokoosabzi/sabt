# SABT — Domain Model

Version: 0.1

## Entity map
Project -> Appointments, Operations, enabled Operation Types
Person -> reusable master data; referenced by Operation Parties
Property -> reusable master data; referenced by Contracts
Appointment -> 0..N Operations
Operation -> 0..1 Contract, N Parties, 1 Property context, N Documents, N Custom Field values, N Audit events
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
