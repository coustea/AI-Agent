## MODIFIED Requirements

### Requirement: PathService calls generate_node instead of run
PathService.generate_node_resource() SHALL call `agent.generate_node(NodeInput)` instead of `agent.run(WorkerState)`. The `_generate_auxiliary_resource_payload()` method SHALL be deleted and replaced with `build_node_input()`, `save_node_result()`, and direct agent invocation.

#### Scenario: PathService builds NodeInput from node and tutorial
- **WHEN** PathService generates a node resource
- **THEN** it SHALL construct a NodeInput with path_goal, node_title, knowledge_points, weak_knowledge_points, generation_focus, tutorial_title, tutorial_markdown, and profile

#### Scenario: PathService does not flatten context into learning_need
- **WHEN** PathService calls an agent for node resource generation
- **THEN** it SHALL NOT concatenate path.goal, node.title, and tutorial content into a single string

#### Scenario: Failed result is not saved
- **WHEN** agent.generate_node() returns AgentResult with success=False
- **THEN** PathService SHALL NOT save a PathNodeResource record and SHALL raise ValueError

### Requirement: Path node resource types are content, mindmap, ppt, code
`AuxiliaryResourceRequest.resource_type` SHALL be `Literal["content", "mindmap", "ppt", "code"]`. `AUX_RESOURCE_TYPES` SHALL be `{"content", "mindmap", "ppt", "code"}`.

#### Scenario: Reading and quiz are not supported
- **WHEN** a request with resource_type "reading" or "quiz" is submitted
- **THEN** the system SHALL reject it with a validation error

#### Scenario: Content resource type is supported
- **WHEN** a request with resource_type "content" is submitted
- **THEN** PathService SHALL call ContentAgent.generate_node()

### Requirement: PathNodeResource has generation status fields
PathNodeResource SHALL have `summary: str | None`, `status: str` (default "completed"), `error_message: str | None`, and `input_json: dict | None` (JSONB). init_schema.sql SHALL be updated with matching columns and a GIN index on input_json.

#### Scenario: Successful resource saved with status
- **WHEN** a node resource is saved after successful generation
- **THEN** the record SHALL have status="completed", summary from AgentResult, and input_json containing the NodeInput snapshot

#### Scenario: Failed resource not saved but error tracked
- **WHEN** generation fails
- **THEN** no PathNodeResource SHALL be created (the caller raises ValueError)

### Requirement: Frontend path resource buttons driven by resource_policy
LearningPathNode.vue SHALL render resource buttons from `node.resource_policy.required_resource_types` and `optional_resource_types`, not from a hardcoded list. Supported types are content, mindmap, ppt, code.

#### Scenario: Buttons reflect resource policy
- **WHEN** a node has resource_policy with required_resource_types=["content", "ppt"] and optional_resource_types=["mindmap", "code"]
- **THEN** 4 buttons SHALL be rendered: 生成节点讲义, 生成 PPT, 生成思维导图, 生成代码示例

#### Scenario: Only policy types shown
- **WHEN** a node has resource_policy with required_resource_types=["content"]
- **THEN** only the 生成节点讲义 button SHALL be rendered

### Requirement: PathResourceDetail supports content, mindmap, ppt, code
PathResourceDetail.vue SHALL render content, mindmap, ppt, and code resource types with appropriate view components.

#### Scenario: Content resource rendered
- **WHEN** a path resource has resource_type "content"
- **THEN** it SHALL be rendered using a Markdown view component

#### Scenario: Code resource rendered
- **WHEN** a path resource has resource_type "code"
- **THEN** it SHALL be rendered using a CodeView component
