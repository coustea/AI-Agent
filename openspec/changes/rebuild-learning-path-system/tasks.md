## 1. Rebuild path domain data model

- [x] 1.1 Add new ORM models and database schema for `learning_paths`, `path_nodes`, `path_node_tutorials`, `path_node_questions`, and `path_node_resources`
- [x] 1.2 Remove legacy learning-path model usage from initialization and path-domain wiring
- [x] 1.3 Add database constraints and indexes for active-path lookup, node ordering, current tutorials, and node-resource retrieval

## 2. Rebuild learning-path backend services and APIs

- [x] 2.1 Create a new learning-path service module for path creation, current-path lookup, and path-history management
- [x] 2.2 Create node-learning service logic for tutorial generation, remediation generation, reinforced tutorial generation, and node progression rules
- [x] 2.3 Create node-question service logic for five-question generation, quiz submission, scoring, and repeated-failure handling
- [x] 2.4 Create node-resource service logic for optional mindmap, PPT, and code-example generation and retrieval
- [x] 2.5 Expose new APIs for path entry, current path, path history, node learning workspace, node quiz submission, and node auxiliary resources

## 3. Rebuild learning-path frontend flows

- [x] 3.1 Replace the current single-page path flow with a path entry page, a path overview page, and a node learning page
- [x] 3.2 Connect the path overview page to the new current-path and path-history APIs
- [x] 3.3 Connect the node learning page to tutorial generation, quiz submission, remediation, reinforced tutorial, and auxiliary resource APIs
- [x] 3.4 Remove legacy path-resource history/detail coupling and any remaining UI logic that depends on the old path-binding model

## 4. Restore learning signals and regression coverage

- [x] 4.1 Reconnect learning-path quiz outcomes and weak-knowledge signals to tutoring profile updates
- [x] 4.2 Add backend regression tests for path creation, history continuation, tutorial versioning, question rounds, and `completed_with_gaps`
- [x] 4.3 Add frontend/manual verification coverage for the new three-page learning-path flow and repeated node-learning cycles
