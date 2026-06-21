## ADDED Requirements

### Requirement: Coverage gap detection in merge_workers_node
`merge_workers_node` in `app/resource/workflow/nodes.py` SHALL compute a coverage report after all worker agents complete. The coverage report SHALL identify:
1. Which `outline.id` values from `TeachingPlan.outline` are covered by at least one successful worker's `downstream_context.covered_outline_ids`
2. Which `outline.id` values are missing (not covered by any worker)
3. Which missing outline items have `must_not_miss=True`

#### Scenario: All outline items covered
- **WHEN** all outline IDs in the TeachingPlan appear in at least one successful worker's `downstream_context.covered_outline_ids`
- **THEN** no coverage gap warning SHALL be emitted
- **AND** the save node SHALL proceed normally

#### Scenario: Non-critical outline item not covered
- **WHEN** outline item `o3` is not covered by any worker, and `o3.must_not_miss=False`
- **THEN** the merge_workers_node SHALL emit an SSE event with event type `agent`, agent_id `coordinator`, status `running`, and message containing the uncovered outline IDs
- **AND** the resource status SHALL still be eligible for `completed`

#### Scenario: Critical outline item not covered
- **WHEN** outline item `o1` is not covered by any worker, and `o1.must_not_miss=True`
- **THEN** the merge_workers_node SHALL emit an SSE event with event type `agent`, agent_id `coordinator`, status `running`, phase `coverage_gap_warning`, and message listing the critical missing outline titles
- **AND** the final resource status SHALL be `partial_completed` instead of `completed`

### Requirement: Coverage report stored in workflow metadata
The coverage report computed in `merge_workers_node` SHALL be stored in `ParentState` as a new field `coverage_report` and persisted in the `generated_resources.workflow_metadata` JSON field alongside existing `selected_agents`.

#### Scenario: Coverage report in workflow_metadata
- **WHEN** save_node persists generation results
- **THEN** `workflow_metadata` SHALL include a `coverage` key containing at minimum: `covered_outline_ids`, `missing_outline_ids`, and `critical_missing_ids`

### Requirement: must_not_miss consumed in status determination
The `save_generation_results` method in `ResourceRepository` SHALL consider coverage gaps when determining the final resource status. If any `must_not_miss` outline item is not covered by any successful worker, the status SHALL be `partial_completed` regardless of whether all workers succeeded.

#### Scenario: All workers succeed but critical outline uncovered
- **WHEN** all worker agents succeed, but a `must_not_miss` outline item has no coverage in any worker's `downstream_context`
- **THEN** the resource status SHALL be `partial_completed`
- **AND** the `failed_agents` field SHALL include a synthetic entry like `"_coverage_gap"` or similar marker

#### Scenario: All workers succeed and all critical outlines covered
- **WHEN** all worker agents succeed, and all `must_not_miss` outline items are covered
- **THEN** the resource status SHALL be `completed`