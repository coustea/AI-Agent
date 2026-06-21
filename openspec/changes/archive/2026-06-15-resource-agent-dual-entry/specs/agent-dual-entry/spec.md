## ADDED Requirements

### Requirement: BaseResourceAgent provides two public generation methods
BaseResourceAgent SHALL define `generate_resource(input: ResourceInput) -> AgentResult` and `generate_node(input: NodeInput) -> AgentResult` as abstract methods. BaseResourceAgent SHALL NOT define a `run()` method.

#### Scenario: Agent has two entry methods
- **WHEN** a class inherits from BaseResourceAgent
- **THEN** it SHALL implement both `generate_resource` and `generate_node`

#### Scenario: Agent does not expose run
- **WHEN** inspecting BaseResourceAgent's public methods
- **THEN** `run` SHALL NOT exist

### Requirement: AgentResult is the unified output type
AgentResult SHALL have fields: `success: bool`, `content: str`, `file_type: str`, `title: str`, `summary: str`, `summary_data: dict`, `metadata: dict`, `error: str`. All fields except `success` SHALL have defaults.

#### Scenario: Successful generation returns AgentResult
- **WHEN** an agent generates content successfully
- **THEN** it SHALL return AgentResult with success=True, content containing the output, and file_type indicating the format

#### Scenario: Failed generation returns AgentResult
- **WHEN** an agent fails to generate content
- **THEN** it SHALL return AgentResult with success=False, error containing the failure reason, and no empty resource record SHALL be saved

### Requirement: ResourceInput carries multi-agent context
ResourceInput SHALL carry: `resource_id`, `learning_need`, `learning_scenario`, `agent_name`, `agent_config`, `blueprint`, `instruction`, `profile`, `previous_results`. The `previous_results` field SHALL be `dict[str, AgentResult]`.

#### Scenario: ResourceInput contains blueprint and instruction
- **WHEN** ResourceService builds a ResourceInput for a worker agent
- **THEN** the input SHALL contain the PlanningAgent's blueprint and the agent-specific instruction

#### Scenario: ResourceInput contains previous results
- **WHEN** a worker agent runs after other agents in the multi-agent DAG
- **THEN** ResourceInput.previous_results SHALL contain successful results from prior agents

### Requirement: WorkerState and WorkerResult are removed
After this change, the module `app.resource.schemas` SHALL NOT export `WorkerState` or `WorkerResult`.

#### Scenario: No imports of old types
- **WHEN** searching the entire server codebase
- **THEN** no file SHALL import or reference WorkerState or WorkerResult

### Requirement: Planning and Review agents return not-supported for generate_node
PlanningAgent.generate_node() and ReviewAgent.generate_node() SHALL return AgentResult with success=False and an error message stating they are not used for path node generation.

#### Scenario: PlanningAgent.generate_node returns not-supported
- **WHEN** PlanningAgent.generate_node() is called
- **THEN** it SHALL return AgentResult(success=False, error="planning agent is not used for path node resource generation")

#### Scenario: ReviewAgent.generate_node returns not-supported
- **WHEN** ReviewAgent.generate_node() is called
- **THEN** it SHALL return AgentResult(success=False, error="review agent is not used for path node resource generation")
