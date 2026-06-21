## 1. Prepare and Consolidate State and Schemas

- [x] 1.1 Move workflow states (LearnState, PlanState) from workflows/state.py to schemas.py
- [x] 1.2 Move plan validation logic from validation.py to schemas.py
- [x] 1.3 Update schemas.py exports and verify types

## 2. Consolidate Workflows and Agents

- [x] 2.1 Merge learn_workflow.py, plan_workflow.py, agents/planner.py, and agents/node_learning.py into a single new workflows.py file
- [x] 2.2 Reconcile imports inside workflows.py

## 3. Consolidate Service Logic

- [x] 3.1 Merge events.py (SSE Event Bus logic) and service.py into service.py
- [x] 3.2 Update PathService imports to reference workflows.py and schemas.py

## 4. Update API and External References

- [x] 4.1 Update api.py with consolidated imports from app.path.schemas, app.path.service, and app.path.workflows
- [x] 4.2 Search for all other external imports of app.path.* (e.g. app/routes.py, app/chat/) and update them

## 5. Cleanup and Verification

- [x] 5.1 Delete workflows/ and agents/ directories and validation.py, events.py
- [x] 5.2 Run backend pytest suite to verify all path-related tests pass successfully
