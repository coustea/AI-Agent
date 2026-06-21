## 1. Project Initialization & Configurations

- [x] 1.1 Update `package.json` to include scripts, dependencies (`@motion-canvas/core`, `@motion-canvas/2d`, `@motion-canvas/ffmpeg`), and CLI commands
- [x] 1.2 Setup `tsconfig.json` with strict type checking and react/TSX support
- [x] 1.3 Configure `vite.config.ts` to integrate `@motion-canvas/vite-plugin`
- [x] 1.4 Setup styles in `src/styles/theme.ts` with unified light colors, card properties, and margins

## 2. Schema Definitions and Validation

- [x] 2.1 Create TypeScript types for `TeachingVideoPlan` and `TeachingVideoScene` in `src/schema/videoPlan.ts`
- [x] 2.2 Define template definitions and registry schema in `src/schema/templateRegistry.ts`
- [x] 2.3 Populate the template registration data array declaring metadata for all 12 templates

## 3. Base UI Components

- [x] 3.1 Implement `FrameLayout` to draw header (topic/title), content area, subtitle bar, and course tag
- [x] 3.2 Implement `SubtitleBar` to draw subtitles dynamically based on duration and offset
- [x] 3.3 Implement `CodeBlock` supporting line highlighting, syntax/language tags, and output section
- [x] 3.4 Implement structural visualizers: `NodeBox`, `Arrow`, `QueueBox`, `TimelineBar`, and `MetricTable`

## 4. Scene Routing & Timing Orchestration

- [x] 4.1 Implement `TemplateRouter.tsx` to read scene template names and trigger matching animation generators
- [x] 4.2 Create `sceneTiming.ts` to manage timing, render budgets, and transition times
- [x] 4.3 Implement `ErrorScene` as fallback for unregistered templates to prevent browser/process crash

## 5. CS Templates Implementation

- [x] 5.1 Implement `ConceptExplain` template (concept title left, features right, one-sentence bottom)
- [x] 5.2 Implement `ProcessFlow` template (flowchart node highlights, transition arrows)
- [x] 5.3 Implement `CodeWalkthrough` template (code lines walk, state change side panels)
- [x] 5.4 Implement `QuestionSolution` template (steps list, final answer box)
- [x] 5.5 Implement `SummaryCard` template (recap points list, exam focus box)
- [x] 5.6 Implement `ComparisonTable` template (side-by-side attributes, conclusion)
- [x] 5.7 Implement `LinearStructureDemo` template (Queue/Stack operations visualizers)
- [x] 5.8 Implement `LinkedListDemo` template (nodes insertion, node deletion links transition)
- [x] 5.9 Implement `TreeGraphTraversal` template (tree nodes/edges graph highlights, queue/stack state track, visit output)
- [x] 5.10 Implement `ProcessStateTransition` template (5-states diagrams, transition labels, dynamic process flow highlight)
- [x] 5.11 Implement `CpuSchedulingDemo` template (Gantt chart steps, turnaround/waiting metrics)
- [x] 5.12 Implement `ProtocolSequence` template (timeline lines, client/server message arrows)

## 6. Project Verification & Documentation

- [x] 6.1 Create the BFS 5-scene example JSON `src/data/video_plan.example.json`
- [x] 6.2 Write a detailed `README.md` explaining setup, startup, rendering, and Backend orchestration
- [x] 6.3 Verify project compiles and runs on Vite local preview server
