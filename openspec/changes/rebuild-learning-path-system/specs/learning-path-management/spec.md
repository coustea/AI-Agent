## ADDED Requirements

### Requirement: System SHALL create and manage standalone learning paths
The system SHALL store learning paths in a dedicated `learning_paths` domain model that is independent from the legacy course-path tables and resource-binding workflow. Each learning path MUST belong to one user, MUST store the learning goal, and MUST track its current overall progress and active state.

#### Scenario: Create a new learning path from a goal
- **WHEN** a user submits a learning goal from the path entry flow
- **THEN** the system SHALL create a new learning path record for that user and persist the generated node structure for the path

#### Scenario: Only one path is current for daily entry
- **WHEN** a user opens the learning-path module
- **THEN** the system SHALL return the user's latest active learning path as the default path overview

### Requirement: System SHALL preserve multiple learning paths per user
The system SHALL allow a user to own multiple learning paths over time and SHALL preserve old paths for later review and continuation.

#### Scenario: Replan while an active path exists
- **WHEN** a user generates a new learning path while another path is currently active
- **THEN** the system SHALL keep the previous path in history and SHALL make the newly generated path the current active path

#### Scenario: View path history
- **WHEN** a user opens the path history view
- **THEN** the system SHALL return archived and completed learning paths with enough metadata to identify each path and its progress

### Requirement: System SHALL support continuing historical learning paths
The system SHALL allow a user to continue learning from a historical path without resetting its node progress, tutorials, or prior learning results.

#### Scenario: Continue a historical path
- **WHEN** a user chooses to continue a historical path
- **THEN** the system SHALL reactivate that path for the user and SHALL preserve its existing node progression and study records

#### Scenario: Continued path becomes the active overview path
- **WHEN** a historical path is reactivated
- **THEN** the system SHALL treat that path as the user's current path for subsequent learning-path entry
