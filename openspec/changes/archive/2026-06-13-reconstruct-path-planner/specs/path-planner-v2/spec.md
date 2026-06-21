## ADDED Requirements

### Requirement: Single-Pass Path Planning without Resource Policy
The PathPlannerAgent SHALL generate the learning path stages and nodes in a single pass without requiring the LLM to output the `resource_policy` structure.

#### Scenario: Successful Path Generation
- **WHEN** user requests a new learning path
- **THEN** the system generates stages and nodes, leaving `resource_policy` empty, which is then populated by a deterministic backend helper.

### Requirement: Capstone Project and Pre-Check Knowledge Fields
The AgentLearningPathPlan schema SHALL include `capstone_project` (title, description) and `pre_check_knowledge` (list of strings) to define target goals and prerequisites.

#### Scenario: Fields populated in response
- **WHEN** the path generation completes successfully
- **THEN** the persisted learning path contains the custom `capstone_project` and `pre_check_knowledge` fields in the response.
