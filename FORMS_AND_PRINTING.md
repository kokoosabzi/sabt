# FORMS_AND_PRINTING.md

## 1. Purpose

This document defines the architecture for Form Designer, Print Templates, PDF generation, direct printing, branding, QR generation, dynamic fields, validation, permissions, audit, and reproducibility.

The subsystem is a controlled template/rendering system integrated with Projects, Operation Types, Operations, Documents, QR payloads, and audit. It is not a general-purpose word processor.

## 2. Core Principles

1. Templates are configuration, not business records.
2. Rendering is server-side and authoritative.
3. Rendering must be deterministic for the same approved template revision and immutable source version.
4. Templates reference approved data fields; they never execute arbitrary code or queries.
5. User-facing layout units are millimeters; PDF rendering uses points.
6. Persian/RTL and mixed RTL/LTR text are first-class requirements.
7. Historical generated PDFs must remain reproducible after later template, branding, Person, or Property changes.
8. Generated files live in filesystem storage; metadata lives in SQLite.
9. QR is configurable per template and generated server-side.
10. Permissions are enforced on the server.
11. Sensitive configuration and generation actions are audited.

## 3. Scope

### V1 includes

- Full drag/drop designer
- Exact X/Y/W/H positioning
- A4 portrait and landscape
- Margins and print-safe area
- Static and dynamic text
- Images and logos
- QR
- Lines and rectangles
- Tables/repeating rows
- Headers/footers
- Page numbers
- Conditional visibility
- RTL/LTR direction control
- PDF preview and generation
- Direct printing through the host environment
- Template validation
- Template activation/deactivation
- Project and Operation Type assignment
- Permissions, concurrency, and audit
- Generated PDF metadata and hashing

### V1 excludes

- Public QR verification site
- Public document download links
- Arbitrary JavaScript/Python in templates
- Cloud rendering
- Collaborative editing
- Full word-processor functionality
- Electronic signature infrastructure
- External printer-server integration
- SMS/email/WhatsApp delivery
- OCR/layout recognition of arbitrary uploaded forms

The architecture should remain extensible without requiring these features in V1.

## 4. Template Scope and Resolution

A Print Template may be:

- System/base
- Project-specific
- Operation-Type-specific
- Project + Operation-Type-specific

Recommended resolution priority:

1. Active Project + Operation Type template
2. Active Project template
3. Active Base/System template

If multiple templates are eligible at the same priority, the system must not silently choose one. It must require an explicit default or report a configuration conflict.

Templates should be associated with Project and Operation Type through explicit configuration rather than hard-coded assumptions.

## 5. Template Versioning

Print templates require immutable revisions even though ordinary Document file versioning does not.

Each logical template has revisions such as Revision 1, Revision 2, etc. A revision should contain:

- template ID
- revision number
- schema version
- normalized definition payload
- definition hash
- created by / created at
- status
- validation result/report
- activation metadata
- optional change note

A revision already used by a generated artifact must never be mutated. Editing creates a new revision.

Historical generated PDFs reference the exact template revision used.

## 6. Coordinate System

### User-facing

All layout dimensions are entered and displayed in mm:

- X
- Y
- Width
- Height
- margins
- page dimensions

### Internal

PDF rendering uses points:

pt = mm × 72 / 25.4

The conversion belongs to one shared rendering utility.

### Origin

Recommended designer origin:

- top-left of page
- X grows right
- Y grows downward

PDF-library coordinate inversion is isolated inside the renderer.

## 7. Page Definition

A template revision defines:

- page width/height
- orientation
- margins
- printable/safe area
- page background
- optional bleed for future use

V1 supports:

- A4 portrait
- A4 landscape

The model should permit A3, Letter, Legal, and custom sizes later.

## 8. Designer Elements

Each element has a stable element ID and persisted geometry.

### Static Text

Properties include:

- text
- font family
- size
- weight
- italic/underline
- alignment
- direction
- line height
- vertical alignment
- X/Y/W/H
- visibility
- optional rotation if later supported

### Dynamic Field

References an allow-listed data path, for example:

- Operation.registration_number
- Operation.contract_number
- Operation.created_at
- Project.name
- Person.full_name
- Property.address
- Contract.contract_number
- Party(role=Buyer).full_name

Dynamic fields must never become arbitrary database queries.

### Image

Properties:

- source
- X/Y/W/H
- fit mode
- preserve aspect ratio
- alignment
- visibility

### Logo

Resolution hierarchy:

1. Template-specific logo
2. Project logo
3. System logo

### QR

Properties:

- enabled
- payload definition
- X/Y
- width/height
- error correction
- quiet zone
- visibility condition

QR payload is generated by the backend.

### Lines and Rectangles

Support position, dimensions, stroke, border style, fill, and visibility.

### Tables / Repeating Rows

Support controlled collections such as:

- operation parties
- contract parties
- documents
- explicitly supported custom-field collections

Properties include column definitions, widths, header/row styles, wrapping, repeated header, minimum row height, and overflow behavior.

### Header/Footer

Support repeated headers, footers, page number, and total page count where supported.

## 9. Positioning and Layering

Every visual element stores:

- element ID
- type
- X/Y/W/H
- z-index/layer
- locked flag
- visibility condition

Designer operations:

- drag
- resize
- align
- distribute
- duplicate
- delete
- move forward/backward
- lock/unlock
- optional grid/snap

Persisted definitions must not depend on DOM coordinates.

## 10. Dynamic Binding

Approved binding namespaces:

- system
- project
- operation
- operation_version
- contract
- property
- parties
- documents
- appointment
- custom_fields
- branding

Binding resolution:

1. validate field path
2. authorize access
3. resolve value
4. format value
5. render value

Templates must not bypass normal permission checks.

## 11. Formatting

Dynamic values support explicit formatting for:

- Persian/Gregorian dates
- Jalali display dates
- time
- numbers
- registration numbers
- contract numbers
- booleans
- phone numbers
- addresses
- custom fields

Stored timestamps remain canonical Gregorian according to the final timezone policy. Printed business presentation may be Jalali.

## 12. Persian, RTL and Fonts

Rendering must support:

- Persian/Arabic shaping
- bidirectional text
- RTL paragraphs
- mixed Persian/Latin content
- configurable Persian digits
- LTR technical values such as IDs, URLs, and codes

Fonts are managed server-side. Templates reference known font families.

Before activation:

- required fonts must exist
- missing fonts are validation errors
- production and preview use the same renderer
- embedded fonts should be used where licensing permits

## 13. Overflow

Renderer must detect:

- text overflow
- table overflow
- image overflow
- unexpected pagination

Critical business fields must not be silently clipped or truncated.

V1 supports controlled wrapping, configurable overflow behavior, warnings for risky layouts, and hard errors where safe rendering is impossible.

## 14. Conditional Visibility

Conditions may depend on approved facts such as:

- Contract exists
- party with role exists
- field has a value
- Operation Type
- Project
- restriction state
- document existence

Conditions use a restricted expression engine with:

- allow-listed operators
- predictable null behavior
- bounded evaluation
- no writes
- no network
- no filesystem access
- no executable code

## 15. Repeating Data and Pagination

Repeating content is rendered by the backend.

When content crosses pages:

- rows should remain intact where possible
- table headers repeat
- page count is recalculated
- page numbers and footers remain correct

Long collections must never produce an invalid PDF.

## 16. Template Validation

Activation requires successful validation.

### Structure

- supported schema version
- required metadata
- valid page definition
- unique element IDs
- supported element types

### Geometry

- numeric valid X/Y/W/H
- no invalid dimensions
- safe-area warnings where appropriate
- unsupported rotation rejected

### Data

- dynamic fields exist in the approved registry
- conditions are valid
- collection bindings are valid
- Operation Type compatibility is valid

### Assets

- fonts exist
- logos/assets exist or valid fallback exists
- references are authorized

### QR

- payload definition valid
- required fields available
- dimensions valid

### Security

- no executable code
- no arbitrary SQL/query
- no arbitrary filesystem path
- no external URL fetch

Validation results are Error, Warning, or Info. Errors block activation/generation.

## 17. Preview Flow

1. Open designer.
2. Select Project/Operation Type context.
3. Load draft revision.
4. Edit layout.
5. Select sample Operation/preview data.
6. Backend validates.
7. Backend renders preview PDF.
8. UI displays preview.
9. User corrects issues.
10. Save draft revision.
11. Authorized user activates revision.

Preview uses the same renderer as final generation.

## 18. Activation

Activation requires:

1. permission check
2. validation
3. asset validation
4. Operation Type compatibility check
5. template conflict/default check
6. creation of immutable revision
7. activation
8. audit
9. cache refresh if applicable

Deactivation never modifies historical generated files.

## 19. Generated PDF Lifecycle

Conceptual lifecycle:

Requested -> Validating -> Rendering -> Generated -> Stored

Failure states:

- Validation Failed
- Rendering Failed
- Storage Failed

Metadata should include:

- generated document ID
- source operation ID
- source operation version ID where applicable
- template ID
- template revision ID
- generation timestamp
- generated by
- storage key
- MIME type
- byte size
- SHA-256
- page count where available
- status
- error details where applicable

PDF files are stored in managed filesystem storage, not SQLite BLOBs by default.

## 20. Reproducibility

A generated PDF must be traceable to:

- Operation
- Operation Version
- Print Template
- Template Revision
- generator/application version where practical
- timestamp
- user

For finalized Operations, rendering historical values must use the immutable finalized snapshot/version.

Later Person, Property, Project branding, or template changes must not silently alter an existing generated PDF.

## 21. Direct Printing

V1 supports:

- Generate PDF
- Preview/open PDF
- Direct print through the host environment

The backend creates the canonical PDF. Printer selection and OS-specific printer configuration may remain client-side.

## 22. Branding

Branding hierarchy:

1. System
2. Project
3. Template-specific

Assets may include:

- logo
- alternate logo
- stamp/seal
- header image
- footer image

Metadata includes asset ID, scope, type, storage key, MIME type, dimensions, hash, active state, and audit data.

Branding changes affect future renders only.

## 23. QR Architecture

QR is an output element, not a standalone business record.

Configuration includes:

- payload fields
- payload version
- checksum/signature mode
- size
- position
- error correction
- visibility

Payload contains only minimum required information. Possible values:

- application/system identifier
- project identifier
- operation identifier
- registration number if available
- contract number if appropriate
- payload version
- issued-at timestamp if needed
- checksum/signature

Do not include unnecessary personal data.

V1 supports:

- checksum for accidental corruption detection
- cryptographic signature/HMAC where server-side secrets are available

Checksum detects accidental corruption. Signature detects unauthorized modification when verification capability exists.

No public verification URL is required in V1.

## 24. QR Security

QR generation is server-side.

Templates cannot:

- choose signing keys
- access secrets
- execute code
- fetch external URLs

Key material is application configuration, never template data.

If signing is enabled:

- support key rotation
- identify key/version where necessary
- keep verification deterministic

## 25. Permissions

Suggested permissions:

- template.view
- template.create
- template.edit
- template.validate
- template.activate
- template.deactivate
- template.delete
- template.preview
- template.generate
- template.print
- template.manage_assets

Generation permission does not imply edit/activation permission.

Historical generated PDFs follow document access rules.

## 26. Concurrency

Template editing is configuration-sensitive.

Use:

- optimistic locking for normal edits
- optional short-lived edit locks
- revision-based saves
- no silent overwrite

A stale save must be rejected and reported. Any privileged overwrite must be explicit.

Activation always targets a known immutable revision.

## 27. Audit

At minimum audit:

- template creation
- revision creation/edit
- validation
- activation/deactivation
- archive/delete
- asset add/replace/archive
- PDF generation/failure
- QR configuration changes
- branding changes
- direct print where policy requires it

Audit records include actor, timestamp, project/context, entity, action, result, relevant revision/version IDs, and reason where required.

## 28. Database Alignment

Reserve or implement these concepts.

### print_templates

- id
- project_id nullable
- operation_type_id nullable
- name
- code
- description
- active_revision_id nullable
- status
- created_by
- created_at
- updated_at
- version

### print_template_revisions

Recommended dedicated table:

- id
- print_template_id
- revision_number
- schema_version
- definition_json
- definition_hash
- validation_status
- validation_report_json
- created_by
- created_at
- activated_by nullable
- activated_at nullable
- status

This is separate from ordinary Document file versioning.

### generated_documents

- id
- operation_id
- operation_version_id nullable
- print_template_id
- template_revision_id
- file_storage_key
- mime_type
- size_bytes
- sha256
- page_count
- status
- generated_by
- generated_at
- error_code nullable
- error_message nullable

These definitions must be reconciled with DATABASE_SCHEMA.md during implementation.

## 29. Storage

Recommended:

storage/
- templates/
- branding/
- generated/
- documents/
- temp/

Generated PDF paths should use stable internal identifiers, for example:

storage/generated/{project_id}/{operation_id}/{generated_document_id}.pdf

Never trust user-provided filenames as filesystem paths.

## 30. File Integrity and Safety

For template assets and generated PDFs:

- calculate SHA-256
- store hash in metadata
- use generated internal storage keys
- prevent path traversal
- never expose arbitrary filesystem paths
- validate MIME/type and size
- enforce storage limits

## 31. API Boundary

The frontend calls explicit backend services. Conceptual endpoints:

- GET /templates
- POST /templates
- GET /templates/{id}
- POST /templates/{id}/revisions
- POST /templates/{id}/validate
- POST /templates/{id}/activate
- POST /templates/{id}/deactivate
- POST /templates/{id}/preview
- POST /operations/{id}/generate-document
- GET /generated-documents/{id}
- POST /generated-documents/{id}/print where supported

Exact route naming may change; rendering and authorization remain server-side.

## 32. Rendering Pipeline

Request
-> authorization
-> load Operation/version
-> resolve Project/Operation Type
-> resolve template revision
-> validate compatibility
-> resolve authorized data
-> resolve branding/assets
-> resolve dynamic fields
-> evaluate safe conditions
-> build render model
-> generate QR
-> render PDF
-> validate output
-> calculate hash
-> store file
-> store metadata
-> audit
-> return generated document reference

A failed render must not create a misleading successful generated-document record.

## 33. Determinism

For reproducible output:

- fixed renderer version/configuration
- fixed fonts
- normalized template definition before hashing
- no network-dependent assets
- no implicit current-time fields
- generation timestamp stored separately
- immutable source version for finalized Operations

If current time is intentionally rendered, it must be explicit and generation time must be recorded.

## 34. Error Codes

Examples:

- TEMPLATE_INVALID
- TEMPLATE_REVISION_NOT_ACTIVE
- FIELD_NOT_ALLOWED
- FIELD_NOT_FOUND
- ASSET_NOT_FOUND
- FONT_NOT_AVAILABLE
- QR_PAYLOAD_INVALID
- RENDER_OVERFLOW
- PDF_RENDER_FAILED
- STORAGE_FAILED
- STALE_TEMPLATE_REVISION

UI errors must be understandable; secrets and internal filesystem details must not be exposed.

## 35. V1 Element Set

Prioritize:

1. Static text
2. Dynamic text
3. Image
4. Logo
5. QR
6. Line
7. Rectangle
8. Table/repeating rows
9. Header/footer
10. Page number
11. Conditional visibility

Advanced vector graphics, charts, signatures, arbitrary rotation, and complex nested layouts can be added later.

## 36. Acceptance Criteria

V1 is acceptable when:

- administrator can create templates
- full drag/drop positioning works
- exact X/Y/W/H are editable in mm
- A4 portrait/landscape work
- approved dynamic fields render
- Persian and mixed RTL/LTR render correctly
- logo fallback hierarchy works
- QR can be positioned/sized and is integrity protected
- invalid templates are blocked
- preview and final rendering use the same engine
- authorized users can activate revisions
- generated PDFs record source Operation and exact template revision
- historical PDFs remain unchanged
- PDF files are outside SQLite with metadata in SQLite
- direct printing is available through the host environment
- sensitive actions are audited
- concurrent edits cannot silently overwrite
- arbitrary executable template code is impossible

## 37. Open Decisions

1. Exact PDF/rendering library.
2. Font licensing and bundled font set.
3. Exact template JSON schema.
4. Exact revision-table implementation details.
5. QR library.
6. HMAC vs asymmetric signature for V1.
7. Windows printer integration strategy.
8. Generated-document deletion vs archival policy.
9. Final template-resolution precedence/default policy.
10. Page-number rendering strategy.

These choices must not weaken the architectural invariants above.
