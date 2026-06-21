## ADDED Requirements

### Requirement: Auxiliary resource types SHALL include content and reading
The `AUX_RESOURCE_TYPES` set SHALL include `content` and `reading` in addition to the existing `mindmap`, `code`, and `ppt` types.

#### Scenario: Content resource generation succeeds
- **WHEN** a student requests a `content` type auxiliary resource for a node
- **THEN** the system SHALL accept the request and generate the resource using the content Agent

#### Scenario: Reading resource generation succeeds
- **WHEN** a student requests a `reading` type auxiliary resource for a node
- **THEN** the system SHALL accept the request and generate the resource using the reading Agent

#### Scenario: Quiz type is still not available via resource endpoint
- **WHEN** a student requests a `quiz` type auxiliary resource
- **THEN** the system SHALL reject the request, as quiz is handled by the dedicated questions endpoint
