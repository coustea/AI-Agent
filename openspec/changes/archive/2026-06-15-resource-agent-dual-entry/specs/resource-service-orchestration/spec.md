## MODIFIED Requirements

### Requirement: ResourceService calls generate_resource instead of run
ResourceService SHALL call `agent.generate_resource(ResourceInput)` instead of `agent.run(WorkerState)`. All WorkerState construction in service.py SHALL be replaced with ResourceInput construction.

#### Scenario: Worker agent called with ResourceInput
- **WHEN** ResourceService runs a worker agent in the multi-agent DAG
- **THEN** it SHALL construct a ResourceInput and call agent.generate_resource(resource_input)

#### Scenario: Planning agent called with ResourceInput
- **WHEN** ResourceService runs the planning agent
- **THEN** it SHALL construct a ResourceInput with agent_config containing enabled_agents and call planning_agent.generate_resource(planning_input)

#### Scenario: Review agent called with ResourceInput
- **WHEN** ResourceService runs the review agent for pre-review or PPT review
- **THEN** it SHALL construct a ResourceInput with agent_config containing review_envelope and call review_agent.generate_resource(review_input)

### Requirement: run_single_agent_generation is deleted
The function `run_single_agent_generation` SHALL be removed from service.py.

#### Scenario: run_single_agent_generation does not exist
- **WHEN** searching service.py for run_single_agent_generation
- **THEN** no match SHALL be found

### Requirement: items.py and review.py use AgentResult
`items.py` SHALL import and use `AgentResult` instead of `WorkerResult`. `review.py` SHALL accept `dict[str, AgentResult]` where it currently accepts `dict[str, WorkerResult]`. Accessed field names remain the same.

#### Scenario: content_envelope accepts AgentResult
- **WHEN** content_envelope is called with an AgentResult
- **THEN** it SHALL read success, content, file_type, title, summary, summary_data, metadata fields (same names as WorkerResult)

#### Scenario: build_pre_audit_envelope accepts AgentResult dict
- **WHEN** build_pre_audit_envelope is called with dict[str, AgentResult]
- **THEN** it SHALL access the same fields as before (success, content, title, summary)
