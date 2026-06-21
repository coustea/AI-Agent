## ADDED Requirements

### Requirement: AgentAssignment model definition
The system SHALL define an `AgentAssignment` Pydantic model in `app/resource/schemas/plan.py` with the following fields:

| Field | Type | Description |
|-------|------|-------------|
| `agent_id` | `str` | The agent identifier (e.g. "content", "quiz", "ppt") |
| `assigned_outline_ids` | `list[str]` | Outline IDs this agent MUST cover |
| `focus_instruction` | `str` | Precise instruction for what this agent should focus on |
| `style_constraint` | `str` | Style directives specific to this agent (e.g. "案例驱动，先直觉后形式化") |
| `boundary_notes` | `list[str]` | Agent-specific boundary reminders (max 6 items) |
| `key_points_emphasis` | `list[str]` | Knowledge points this agent should emphasize (max 8 items) |
| `avoid_overlap_with` | `list[str]` | Agent IDs this agent should avoid duplicating content with |

The model SHALL use `model_config = ConfigDict(extra="forbid")`.

#### Scenario: AgentAssignment created by Planning Agent
- **WHEN** Planning Agent generates a TeachingPlan for a user request with selected agents ["content", "quiz", "mindmap"]
- **THEN** the `agent_assignments` field SHALL contain exactly 3 `AgentAssignment` entries, one per selected agent
- **AND** each `assigned_outline_ids` SHALL reference only outline IDs that exist in `TeachingPlan.outline`
- **AND** the union of all `assigned_outline_ids` across assignments SHALL cover at least all `must_not_miss` outline items

#### Scenario: AgentAssignment with empty avoid_overlap_with
- **WHEN** a content agent has no specific overlap concerns
- **THEN** `avoid_overlap_with` SHALL be an empty list `[]`

### Requirement: TeachingPlan includes agent_assignments
`TeachingPlan` SHALL include an `agent_assignments: list[AgentAssignment]` field with `default_factory=list`.

#### Scenario: TeachingPlan with assignments
- **WHEN** Planning Agent runs in multi-agent mode
- **THEN** `TeachingPlan.agent_assignments` SHALL contain one entry per enabled worker agent
- **AND** each entry's `agent_id` SHALL match one of the enabled agent IDs

#### Scenario: TeachingPlan in single-agent / path-node mode
- **WHEN** Planning Agent is not used (path-node generation uses `generate_node()` directly)
- **THEN** `TeachingPlan.agent_assignments` SHALL default to an empty list

### Requirement: TeachingPlan removes unused fields
`TeachingPlan` SHALL NOT contain `audience`, `difficulty`, or `boundaries` fields. These fields are removed from the Pydantic model entirely.

`TeachingPlan` SHALL use `model_config = ConfigDict(extra="ignore")` to allow deserialization of old records that still contain these fields without raising validation errors.

#### Scenario: Old TeachingPlan JSON with removed fields
- **WHEN** a TeachingPlan JSON from database contains `audience` or `difficulty` or `boundaries` fields
- **THEN** `TeachingPlan.model_validate(plan_data)` SHALL succeed without error
- **AND** those extra fields SHALL be silently ignored

#### Scenario: Planning Agent output schema
- **WHEN** Planning Agent generates a TeachingPlan
- **THEN** the JSON output SHALL NOT contain `audience`, `difficulty`, or `boundaries` keys
- **AND** the JSON SHALL contain an `agent_assignments` key with a list of AgentAssignment objects

### Requirement: Worker agents consume assignment slices instead of full TeachingPlan
Each Worker Agent (`content`, `mindmap`, `quiz`, `code`, `reading`) SHALL receive only its own `AgentAssignment` and the relevant outline slice (items matching `assigned_outline_ids`) instead of the entire TeachingPlan JSON.

The function `build_resource_context()` in `app/resource/agents/common.py` SHALL be modified to:
1. Look up the agent's `AgentAssignment` from `TeachingPlan.agent_assignments`
2. Filter `TeachingPlan.outline` to only include items whose `id` is in the assignment's `assigned_outline_ids`
3. Inject the assignment's `focus_instruction`, `style_constraint`, `boundary_notes`, and `key_points_emphasis` into the prompt context
4. Inject the agent's `avoid_overlap_with` as a "do not duplicate" directive

#### Scenario: Content agent receives only its assignment
- **WHEN** ContentAgent runs with a TeachingPlan that has `agent_assignments` containing `{"agent_id": "content", "assigned_outline_ids": ["o1", "o3"], "focus_instruction": "以案例驱动讲解..."}`
- **THEN** the prompt context SHALL include only outline items o1 and o3
- **AND** the prompt SHALL include the focus_instruction, style_constraint, boundary_notes, and avoid_overlap_with fields
- **AND** the prompt SHALL NOT include outline items o2, o4, o5 that are assigned to other agents

#### Scenario: Fallback when agent_assignments is empty
- **WHEN** `TeachingPlan.agent_assignments` is empty (e.g., path-node mode or old data)
- **THEN** `build_resource_context()` SHALL fall back to the current behavior of injecting the full TeachingPlan
- **AND** `outline_ids_from_plan()` SHALL return all outline IDs as before

### Requirement: CodeAgent uses assigned_outline_ids instead of keyword matching
`CodeAgent.generate_resource()` SHALL use `AgentAssignment.assigned_outline_ids` for outline selection when `agent_assignments` is available, replacing the current `select_outline_ids_by_keywords()` logic.

#### Scenario: CodeAgent with assignment
- **WHEN** CodeAgent has an assignment with `assigned_outline_ids: ["o2", "o4"]`
- **THEN** the handoff `covered_outline_ids` SHALL be `["o2", "o4"]`
- **AND** `select_outline_ids_by_keywords()` SHALL NOT be called

#### Scenario: CodeAgent without assignment (fallback)
- **WHEN** `TeachingPlan.agent_assignments` is empty
- **THEN** CodeAgent SHALL fall back to `select_outline_ids_by_keywords()` as currently implemented
