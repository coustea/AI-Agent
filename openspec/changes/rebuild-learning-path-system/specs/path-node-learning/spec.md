## ADDED Requirements

### Requirement: System SHALL separate path overview from node learning
The system SHALL support a path overview experience and a node learning experience as distinct flows. The path overview SHALL focus on route structure and progression, while node learning SHALL focus on the current tutorial, test, reinforcement, and node-specific resources.

#### Scenario: Enter node learning from path overview
- **WHEN** a user selects an available node from the path overview
- **THEN** the system SHALL load that node's learning workspace and current tutorial context

### Requirement: System SHALL generate node tutorials on demand
The system SHALL NOT generate all node content during path creation. It SHALL generate the primary tutorial only when a user actually starts learning a node.

#### Scenario: Start learning a node
- **WHEN** a user starts learning a node that does not yet have a primary tutorial
- **THEN** the system SHALL generate and persist a primary tutorial for that node

#### Scenario: Reopen a node with an existing current tutorial
- **WHEN** a user reopens a node that already has a current tutorial
- **THEN** the system SHALL return the persisted current tutorial instead of generating a new one

### Requirement: System SHALL support remediation and reinforced tutorials
The system SHALL support additional tutorial variants for a node after failed measurement. A first failed quiz cycle SHALL generate a remediation tutorial focused on weak knowledge points. A second failed quiz cycle SHALL generate a reinforced tutorial derived from the original tutorial and focused on weak knowledge points identified from prior wrong answers.

#### Scenario: First failed node quiz
- **WHEN** a user fails the first quiz cycle for a node
- **THEN** the system SHALL generate and persist a remediation tutorial for that node

#### Scenario: Second failed node quiz
- **WHEN** a user fails the second quiz cycle for a node
- **THEN** the system SHALL generate and persist a reinforced tutorial linked to the original tutorial for that node

#### Scenario: Reinforced tutorial explains its origin
- **WHEN** the current node tutorial is a reinforced tutorial
- **THEN** the system SHALL expose metadata indicating that the tutorial was generated from prior wrong answers and weak knowledge points

### Requirement: System SHALL advance node progression using quiz results
The system SHALL use node quiz results as the primary progression rule. Each node quiz MUST contain five single-choice questions. The system SHALL mark the node as passed when the learner answers at least three questions correctly.

#### Scenario: Pass a node quiz
- **WHEN** a learner submits five node questions and answers at least three correctly
- **THEN** the system SHALL mark the node as completed and unlock the next eligible node

#### Scenario: Fail a node quiz
- **WHEN** a learner submits five node questions and answers fewer than three correctly
- **THEN** the system SHALL keep the node incomplete and trigger the appropriate remediation or reinforcement cycle

### Requirement: System SHALL allow progress after repeated failure with tracked gaps
The system SHALL avoid trapping the learner on one node indefinitely. If a learner still does not pass after the reinforcement cycle, the system SHALL allow progression to the next node while marking the current node as `completed_with_gaps`.

#### Scenario: Progress after repeated failure
- **WHEN** a learner completes the reinforced tutorial cycle and still answers fewer than three questions correctly
- **THEN** the system SHALL mark the node as completed with gaps and SHALL allow the next eligible node to become available

#### Scenario: Gap completion remains distinguishable from normal completion
- **WHEN** a node is progressed after repeated failure
- **THEN** the system SHALL preserve a node status that is distinct from a normal completed node
