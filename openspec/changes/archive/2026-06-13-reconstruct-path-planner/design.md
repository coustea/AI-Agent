## Context

The path planner currently experiences failures due to Xunfei model authorization expiration (`AppIdNoAuthError`). Furthermore, the path generation prompt is overly verbose because it forces the LLM to output a complex `resource_policy` structure for every node. The frontend displays this structure as an interactive graph tree (`PathSkillTree.vue`), which is visually complex and doesn't clearly show the linear sequence of learning.

## Goals / Non-Goals

**Goals:**
- Resolve the LLM authentication issue by switching the backend to Zhipu `glm-4-flash` (using the verified key currently in config).
- Simplify the path planning LLM output schema, reducing response token size and formatting failure rates by 60%.
- Refactor the SQL tables (`learning_paths` and `path_nodes`) to hold `capstone_project_json` and `pre_check_knowledge` fields.
- Redesign the frontend learning path overview into a clean, sequential vertical timeline showing milestones, checklist, and final project.

**Non-Goals:**
- Maintaining backward database compatibility. Old plans will be dropped and tables recreated.
- Modifying resource generation agents themselves; they will still consume the Python-generated resource policies.

## Decisions

### 1. Switch Primary Model to Zhipu GLM-4-Flash
- **Choice**: Configure `models` section in `config.yaml` to point to Zhipu GLM `glm-4-flash`.
- **Rationale**: Zhipu API is verified to work, supports tool calling, JSON mode, and is extremely cost-effective.

### 2. Simplify LLM Output Schema & System Prompt
- **Choice**: Remove `resource_policy` and `priority` from LLM output. Rely on python-based `normalize_path_plan` to build the default policies.
- **Rationale**: Reduces prompt output complexity, prevents formatting errors, and speeds up generation time.

### 3. Add Capstone Project & Pre-Check checklist
- **Choice**: Add `capstone_project` and `pre_check_knowledge` to the LLM response. Persist them in `learning_paths` table using `JSONB` columns.
- **Rationale**: These provide immediate goal orientation and readiness checklists for the user before they begin learning.

### 4. Frontend Timeline Redesign
- **Choice**: Replace ECharts graph chart with a CSS timeline. Use icons (checkmark for completed, blue dot for active, lock icon for locked) to show linear step progression.
- **Rationale**: A linear layout is more intuitive for a curriculum than a dynamic graph network.

## Risks / Trade-offs

- **[Risk] Table schema changes** ──> **[Mitigation]** The user approved dropping older schema data. We will drop and recreate the tables during development.
