# SABT — Logical ERD

Version: 0.1

```text
PROJECT
  | 1
  +----< APPOINTMENT >---- APPOINTMENT_TYPE
  |
  +----< OPERATION >------ OPERATION_TYPE
  |          |
  |          +----< OPERATION_PARTY >---- PERSON
  |          |            |
  |          |            +---- PARTY_ROLE
  |          |
  |          +---- 0..1 CONTRACT >---- PROPERTY
  |          |
  |          +----< DOCUMENT >---- DOCUMENT_TYPE
  |          |
  |          +----< PERSON_SNAPSHOT
  |          +----< PROPERTY_SNAPSHOT
  |          +----< OPERATION_VERSION
  |          +----< AUDIT_EVENT
  |          +----< CUSTOM_FIELD_VALUE
  |          +----< GENERATED_DOCUMENT
  |
  +----< PROJECT_OPERATION_TYPE >---- OPERATION_TYPE
  |
  +----< PROPERTY
  |
  +----< USER_ROLE >---- USER
  |
  +----< PRINT_TEMPLATE
```

## Critical cardinalities
- Project 1:N Appointment
- Appointment 0:N Operation
- Project 1:N Operation
- OperationType N:N Project through ProjectOperationType
- Operation N:N Person through OperationParty
- Operation 0:1 Contract
- Contract N:1 Property, with one Property per Contract
- Operation 1:N Document
- Operation 1:N AuditEvent
- Operation 1:N OperationVersion

## Ownership rule
The Contract owns the optional relationship to Operation through `contracts.operation_id UNIQUE`. This avoids a circular `operations.contract_id` + `contracts.operation_id` relationship.

## Historical rule
Master Person/Property records may change. Finalized OperationVersion plus Person/Property snapshots are the historical source for reproduction of finalized records.

## Deletion rule
Business records are normally archived rather than deleted. Referential integrity must protect finalized history.