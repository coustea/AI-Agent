## 1. Schema & Model Changes

- [x] 1.1 Add `AgentAssignment` Pydantic model to `server/app/resource/schemas/plan.py` with fields: `agent_id`, `assigned_outline_ids`, `focus_instruction`, `style_constraint`, `boundary_notes`, `key_points_emphasis`, `avoid_overlap_with` (ConfigDict extra="forbid")
- [x] 1.2 Add `agent_assignments: list[AgentAssignment]` field (default_factory=list) to `TeachingPlan` in `plan.py`
- [x] 1.3 Remove `audience`, `difficulty`, `boundaries` fields from `TeachingPlan` in `plan.py`
- [x] 1.4 Change `TeachingPlan.model_config` from `extra="forbid"` to `extra="ignore"` for backward compatibility

## 2. Planning Prompt Rewrite

- [x] 2.1 Rewrite `server/app/resource/prompts/planning.md` to instruct LLM to generate `agent_assignments` per enabled agent with precise `assigned_outline_ids`, `focus_instruction`, `style_constraint`, `boundary_notes`, `key_points_emphasis`, `avoid_overlap_with`
- [x] 2.2 Remove references to `audience`, `difficulty`, `boundaries` from planning prompt
- [x] 2.3 Add agent role descriptions to planning prompt so LLM knows each agent's purpose (content→讲解, quiz→题目, mindmap→导图, code→代码示例, reading→阅读材料)

## 3. Worker Agent Slice Consumption

- [x] 3.1 Add `build_agent_assignment_context()` function to `server/app/resource/agents/common.py` — looks up agent's `AgentAssignment`, filters outline slice, injects focus/style/boundary/overlap directives
- [x] 3.2 Modify `build_resource_context()` in `common.py` to use `build_agent_assignment_context()` when `agent_assignments` is non-empty, fall back to current full-plan injection when empty
- [x] 3.3 Modify `ContentAgent.generate_resource()` to use assignment-based context (no outline_ids_from_plan full list)
- [x] 3.4 Modify `MindmapAgent.generate_resource()` to use assignment-based context
- [x] 3.5 Modify `QuizAgent.generate_resource()` to use assignment-based context
- [x] 3.6 Modify `CodeAgent.generate_resource()` to use `assigned_outline_ids` instead of `select_outline_ids_by_keywords()` when assignment available, fallback to keyword matching when not
- [x] 3.7 Modify `ReadingAgent.generate_resource()` to use assignment-based context

## 4. Workflow Node Changes

- [ ] 4.1 Add `coverage_report` field to `ParentState` in `server/app/resource/workflow/state.py`
- [ ] 4.2 Modify `planning_node` in `server/app/resource/workflow/nodes.py` to parse `agent_assignments` from TeachingPlan and inject into state for worker dispatch
- [ ] 4.3 Add coverage gap detection logic to `merge_workers_node` in `nodes.py` — compute covered/missing outline IDs, identify critical missing (must_not_miss=True), emit SSE coverage_gap_warning event
- [ ] 4.4 Modify save logic to set status `partial_completed` when critical outline uncovered, include `_coverage_gap` marker in failed_agents
- [ ] 4.5 Persist coverage report in `workflow_metadata` JSON field alongside `selected_agents`

## 5. Aggregation Agent Adaptation

- [ ] 5.1 Modify `PPTAgent` to consume `agent_assignments` relevant to ppt (if present) for summary context
- [ ] 5.2 Modify `VideoAgent` to consume `agent_assignments` relevant to video (if present) for summary context

## 6. Verification

- [ ] 6.1 Run `npm run build` to verify frontend has no type errors from schema change
- [ ] 6.2 Run `uv run pytest` (excluding pre-existing failures) to verify backend tests pass
- [ ] 6.3 Verify `TeachingPlan.model_validate(old_json_with_audience)` succeeds with `extra="ignore"`
