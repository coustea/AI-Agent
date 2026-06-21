## ADDED Requirements

### Requirement: Node status SHALL transition to in_progress on workspace entry
When a student enters a node workspace via `get_node_workspace` and the node status is `available`, the system SHALL automatically transition the node status to `in_progress` and record the `started_at` timestamp.

#### Scenario: Available node becomes in_progress
- **WHEN** a student accesses a node workspace with node status `available`
- **THEN** the node status SHALL change to `in_progress`, `started_at` SHALL be set to the current UTC timestamp, and the change SHALL be committed to the database

#### Scenario: Already in_progress node remains unchanged
- **WHEN** a student accesses a node workspace with node status `in_progress`
- **THEN** the node status and `started_at` SHALL remain unchanged

#### Scenario: Locked node access is still denied
- **WHEN** a student tries to access a node workspace with node status `locked`
- **THEN** the system SHALL raise an error and deny access, same as before
