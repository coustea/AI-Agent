## ADDED Requirements

### Requirement: NodeInput carries structured node context
NodeInput SHALL carry: `path_id`, `node_id`, `node_key`, `path_title`, `path_goal`, `node_title`, `difficulty`, `mastery_target`, `knowledge_points`, `weak_knowledge_points`, `generation_focus`, `tutorial_title`, `tutorial_summary`, `tutorial_markdown`, `profile`, `agent_config`. NodeInput SHALL NOT carry `existing_resources`, `blueprint`, or `instruction`.

#### Scenario: NodeInput contains tutorial content
- **WHEN** PathService builds a NodeInput for an agent
- **THEN** the input SHALL contain tutorial_title, tutorial_summary, and the full tutorial_markdown (not truncated)

#### Scenario: NodeInput contains knowledge points
- **WHEN** PathService builds a NodeInput from a PathNode and PathNodeTutorial
- **THEN** knowledge_points and weak_knowledge_points SHALL come from the tutorial record, and generation_focus SHALL come from node.resource_policy

#### Scenario: NodeInput does not carry previous results
- **WHEN** NodeInput is constructed
- **THEN** it SHALL NOT have an existing_resources or previous_results field

### Requirement: build_node_context produces structured prompt
`build_node_context(input: NodeInput) -> list[str]` SHALL produce prompt sections including: path goal, node title, knowledge points, weak knowledge points, generation focus, tutorial content, and learner profile.

#### Scenario: Node context includes structured fields
- **WHEN** build_node_context is called with a NodeInput
- **THEN** the output SHALL contain "## 路径目标", "## 当前节点", "## 节点知识点", "## 当前教程" sections with structured field values (not a flattened string)

### Requirement: build_resource_context replaces build_worker_base_context
`build_resource_context(input: ResourceInput) -> list[str]` SHALL produce prompt sections including: learning need, learning scenario, blueprint, instruction, previous results, and learner profile. `build_worker_base_context` SHALL be removed.

#### Scenario: Resource context includes blueprint
- **WHEN** build_resource_context is called with a ResourceInput containing a blueprint
- **THEN** the output SHALL contain a "## 教学蓝图" section with the blueprint JSON

#### Scenario: build_worker_base_context is removed
- **WHEN** searching the codebase for build_worker_base_context
- **THEN** no references SHALL exist
