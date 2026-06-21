## 1. State and schema cleanup

- [x] 1.1 Audit `server/app/chat/schemas.py`, `server/app/chat/runtime.py`, and `server/app/chat/service.py` to identify obsolete context fields, duplicate answer-path state, and unused DTO data introduced by the old route-based graph
- [x] 1.2 Simplify `TutorAgentContext` and `TutorState` so they only carry input fields, preparation results, and final output fields required by the linear pipeline
- [x] 1.3 Remove dead schema fields, helper structures, and runtime assembly code that only existed for the old mutually exclusive routing model

## 2. Agent graph refactor

- [x] 2.1 Rewrite `server/app/chat/agent.py` graph construction to use the linear node chain `classify -> attachment_analysis? -> search? -> answer -> diagram?`
- [x] 2.2 Convert attachment handling into a preparation node that writes attachment analysis results into shared state instead of producing its own final answer path
- [x] 2.3 Convert search handling into a preparation node that writes search result text and source metadata into shared state instead of acting as a parallel answer draft
- [x] 2.4 Replace duplicated direct-answer and attachment-answer logic with one unified answer stage that consumes shared state and still supports tool-augmented generation
- [x] 2.5 Update diagram generation so it only runs after answer completion and consumes final answer output plus existing state context

## 3. Tool and context boundary cleanup

- [x] 3.1 Remove default preloading of learner profile and long-term memory from the initial chat context assembly path
- [x] 3.2 Keep profile and long-term memory available as answer-stage tools, and update prompts so the agent knows they are for on-demand use only
- [x] 3.3 Delete cross-layer memory reads from non-answer nodes and remove old tool wiring or helper code that conflicts with the new responsibility split

## 4. Service and prompt alignment

- [x] 4.1 Update `server/app/chat/service.py` so it prepares only the base tutoring context, persists messages, and delegates linear execution to the refactored agent
- [x] 4.2 Update chat prompts to reflect the new evidence flow: attachments first, optional search enrichment, unified answer, optional post-answer diagram
- [x] 4.3 Remove stale comments, status labels, and logging paths that still describe the old route-based execution model

## 5. Tests and dead code removal

- [x] 5.1 Update existing chat and resource tests to match the new linear execution flow, shared state fields, and on-demand learner context behavior
- [x] 5.2 Add or revise regression tests for the key scenarios: plain answer, attachment-first answer, search-enriched answer, and post-answer diagram generation
- [x] 5.3 Delete unused chat helper functions, obsolete route branches, dead memory-loading code, and any tests that only validate the removed architecture
