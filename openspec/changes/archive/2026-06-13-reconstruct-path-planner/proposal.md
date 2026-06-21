## Why

The current path planning agent uses a single-pass LLM prompt that forces it to generate a verbose, deeply nested `resource_policy` for every node. This causes high token usage, slows down API calls, and is a major cause of API errors/timeouts (especially on Xunfei Spark/Maas). Additionally, the ECharts-based graph tree on the frontend is visually complex and lacks a clear, sequential learning progression. Reconstructing the SQL tables, simplifying the backend LLM outputs, and redesigning the frontend into a step-by-step linear learning timeline will make the feature fast, stable, and user-friendly.

## What Changes

- **Simplified Backend LLM Output**: Remove `resource_policy` generation from the initial LLM path planner agent pass, letting it generate only stages and nodes. A deterministic Python backend helper will populate default resource policies instantly.
- **SQL Table Refactoring**: Refactor `learning_paths` table columns. Add `capstone_project_json` (JSONB) and `pre_check_knowledge` (JSONB) columns to store target real-world projects and pre-requisite checklists.
- **Front-end Redesign**: Replace the ECharts graph tree with a clean, linear, milestone-driven step-by-step timeline interface. Show the custom capstone project, pre-check checklist, and sequential steps with progress tracking.
- **Breaking Database Schema**: This change is **BREAKING** and will recreate tables (`learning_paths`, `path_nodes`), dropping compatibility with older plans to clean up the code.

## Capabilities

### New Capabilities
- `path-planner-v2`: Simplified single-pass path planner and database schema.
- `linear-path-timeline`: Sequential step-by-step timeline rendering with milestone and project tracking.

### Modified Capabilities
<!-- None -->

## Impact

- **Database**: Re-initialization of `learning_paths` and `path_nodes` tables. Old records will be dropped.
- **Backend APIs**: `/api/v1/ai/path-plan/*` response structures will be updated to include capstone projects and pre-check knowledge.
- **Agent Workflows**: `PathPlannerAgent` prompt and schema will be updated, reducing LLM output tokens by ~60%.
- **Frontend Pages**: `LearningPathOverview.vue` will be redesigned, and `PathSkillTree.vue` will be replaced by a linear step-by-step timeline.
