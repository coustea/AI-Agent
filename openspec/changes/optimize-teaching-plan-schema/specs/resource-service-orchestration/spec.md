## MODIFIED Requirements

### Requirement: ResourceService calls generate_resource instead of run
ResourceService SHALL call `agent.generate_resource(ResourceInput)` instead of `agent.run(WorkerState)`. All WorkerState construction in service.py SHALL be replaced with ResourceInput construction. **Additionally**, when `TeachingPlan.agent_assignments` is non-empty, the `ResourceInput` passed to each worker agent SHALL include the agent's specific `AgentAssignment` data in `agent_config["_assignment"]`, and `build_resource_context()` SHALL produce a sliced context instead of the full TeachingPlan.

#### Scenario: Worker agent called with ResourceInput and assignment
- **WHEN** ResourceService runs a worker agent and the TeachingPlan has `agent_assignments`
- **THEN** it SHALL construct a ResourceInput with `agent_config["_assignment"]` containing the agent's `AgentAssignment`
- **AND** `build_resource_context()` SHALL inject only the assigned outline slice and focus directives

#### Scenario: Worker agent called with ResourceInput without assignment
- **WHEN** ResourceService runs a worker agent and `TeachingPlan.agent_assignments` is empty
- **THEN** it SHALL construct a ResourceInput as before (full TeachingPlan injection)

#### Scenario: Planning agent called with ResourceInput
- **WHEN** ResourceService runs the planning agent
- **THEN** it SHALL construct a ResourceInput with agent_config containing enabled_agents and call planning_agent.generate_resource(planning_input)
- **AND** the PlanningAgent SHALL generate `agent_assignments` in its output TeachingPlan

#### Scenario: Review agent called with ResourceInput
- **WHEN** ResourceService runs the review agent for pre-review or PPT review
- **THEN** it SHALL construct a ResourceInput with agent_config containing review_envelope and call review_agent.generate_resource(review_input)

### Requirement: items.py and review.py use AgentResult
`items.py` SHALL import and use `AgentResult` instead of `WorkerResult`. `review.py` SHALL accept `dict[str, AgentResult]` where it currently accepts `dict[str, WorkerResult]`. Accessed field names remain the same. **No change from existing requirement** — this is carried forward unchanged.

#### Scenario: content_envelope accepts AgentResult
- **WHEN** content_envelope is called with an AgentResult
- **THEN** it SHALL read success, content, file_type, title, summary, metadata fields (same names as WorkerResult)

#### Scenario: build_pre_audit_envelope accepts AgentResult dict
- **WHEN** build_pre_audit_envelope is called with dict[str, AgentResult]
- **THEN** it SHALL access the same fields as before (success, content, title, summary)