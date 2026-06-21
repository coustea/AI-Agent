## 1. Setup & Configuration

- [x] 1.1 Update `server/config.yaml` to point the primary text model and API key to Zhipu `glm-4-flash`.
- [x] 1.2 Run the connectivity test suite to verify the Zhipu backend is active and functioning.

## 2. Database Schema Refactoring

- [x] 2.1 Update `server/init_schema.sql` to add `capstone_project_json` and `pre_check_knowledge` columns to the `learning_paths` table.
- [x] 2.2 Update `server/app/infra/models.py` to sync `LearningPath` SQLModel.
- [x] 2.3 Recreate database tables to apply the new schema clean slate.

## 3. Backend Agent & Service Implementation

- [x] 3.1 Update `server/app/path/schemas.py` to add `CapstoneProject` and update `AgentLearningPathPlan` / `AgentPathNode` structures.
- [x] 3.2 Update `server/app/path/agents/planner.py` to simplify the LLM system prompt (removing `resource_policy`) and add capstone project / checklist generation.
- [x] 3.3 Update `server/app/path/service.py` to save new project and checklist fields and trigger Python-based resource policy normalization.
- [x] 3.4 Verify the backend path generation tests pass successfully using pytest.

## 4. Frontend Timeline Redesign

- [x] 4.1 Update `src/features/learning/views/LearningPathOverview.vue` to show the personalized strategy diagnostic card, capstone project targets, and pre-check checklists.
- [x] 4.2 Reconstruct `src/features/learning/components/PathSkillTree.vue` to render a vertical sequential linear timeline instead of the ECharts graph node web.
- [x] 4.3 Verify the entire path generation and sequential UI flow works end-to-end.
