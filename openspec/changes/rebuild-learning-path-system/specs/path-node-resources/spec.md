## ADDED Requirements

### Requirement: System SHALL store node-specific auxiliary resources separately from tutorials
The system SHALL store optional node-specific resources in a dedicated resource model separate from node tutorials and separate from the legacy standalone resource-generation history.

#### Scenario: Persist a generated mindmap
- **WHEN** a user requests a mindmap for a node
- **THEN** the system SHALL generate and persist that mindmap as a node-specific auxiliary resource

#### Scenario: Persist a generated PPT
- **WHEN** a user requests a PPT for a node
- **THEN** the system SHALL generate and persist that PPT as a node-specific auxiliary resource

### Requirement: System SHALL keep auxiliary resources optional and user-triggered
Auxiliary resources SHALL be optional support materials. The system SHALL NOT generate them automatically during path creation or node entry, and SHALL only generate them in response to explicit user actions.

#### Scenario: Create path without auxiliary resources
- **WHEN** a new path is generated
- **THEN** the system SHALL NOT create node auxiliary resources automatically

#### Scenario: Enter node learning without auxiliary resources
- **WHEN** a learner opens a node learning workspace for the first time
- **THEN** the system SHALL show no auxiliary resource records unless the learner has explicitly generated them before

### Requirement: System SHALL keep persisted node resources available for review
The system SHALL persist node auxiliary resources so the learner can revisit them later when reviewing or resuming a path.

#### Scenario: Revisit a node with existing auxiliary resources
- **WHEN** a learner revisits a node that already has persisted auxiliary resources
- **THEN** the system SHALL return the stored resources instead of treating them as missing

#### Scenario: Continue a historical path with node resources
- **WHEN** a learner continues a historical path
- **THEN** the system SHALL preserve and return the node auxiliary resources that were previously generated for that path
