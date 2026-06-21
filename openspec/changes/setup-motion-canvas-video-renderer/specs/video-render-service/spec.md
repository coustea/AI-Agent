## ADDED Requirements

### Requirement: TeachingVideoPlan Schema Validation
The video render service SHALL validate incoming video plans against the `TeachingVideoPlan` schema structure before rendering.

#### Scenario: Valid TeachingVideoPlan JSON
- **WHEN** a valid `video_plan.json` is loaded into the project
- **THEN** validation passes and the TemplateRouter prepares the scenes for rendering

#### Scenario: Invalid TeachingVideoPlan JSON
- **WHEN** the loaded JSON has invalid scene formats or unrecognized template names
- **THEN** validation fails and the renderer fallback to an ErrorScene showing validation errors

### Requirement: Template Registry and Routing
The service SHALL register all animation templates in a `TemplateRegistry` and route each scene to the corresponding template generator.

#### Scenario: Registered template match
- **WHEN** a scene specifies a template named `concept_explain`
- **THEN** the TemplateRouter executes the registered `ConceptExplain` animation generator

#### Scenario: Unrecognized template fallback
- **WHEN** a scene specifies an unregistered template name
- **THEN** the TemplateRouter displays a fallback `ErrorScene` with a warning message on screen

### Requirement: Unified Visual Style and Theme
The service SHALL render animations using a unified light theme with background color `#F8FAFC`, code blocks with background `#F1F5F9`, and main text `#1E293B`.

#### Scenario: Apply theme styles
- **WHEN** a scene is rendered
- **THEN** the background color is `#F8FAFC`, text is `#1E293B`, and cards use `#FFFFFF` with soft shadows

### Requirement: Common Concept Explain Scene Template
The `concept_explain` template SHALL display a prominent concept title on the left side, detailed features on the right, and a one-sentence summary at the bottom.

#### Scenario: Render concept explanation
- **WHEN** the scene `concept_explain` is executed
- **THEN** it animates the title, lists features sequentially, and fades in the one-sentence highlight at the bottom

### Requirement: Common Process Flow Scene Template
The `process_flow` template SHALL display a graph sequence of nodes and connecting arrows that highlight sequentially.

#### Scenario: Render process flow animation
- **WHEN** the scene `process_flow` is executed
- **THEN** nodes are rendered, connecting arrows fade in, and steps highlight sequentially according to the transitions list

### Requirement: Programming Code Walkthrough Scene Template
The `code_walkthrough` template SHALL display a light-theme code panel on the left, an explanation card on the right, and state tracking at the bottom.

#### Scenario: Render code execution walkthrough
- **WHEN** the scene `code_walkthrough` is executed
- **THEN** the compiler code highlights the current line number, displays the explanation, and updates the states (e.g. queue stack visualizers) below the code block

### Requirement: Network Protocol Sequence Scene Template
The `protocol_sequence` template SHALL display vertical participant columns and animate messages moving between participants over time.

#### Scenario: Render TCP handshake sequence
- **WHEN** the scene `protocol_sequence` is executed for a TCP handshake
- **THEN** the screen draws "Client" and "Server" vertical lines, and animates SYN, SYN+ACK, and ACK arrows sequentially from sender to receiver

### Requirement: Operating System CPU Scheduling Scene Template
The `cpu_scheduling_demo` template SHALL display a list of ready processes, execution states, a scheduling Gantt chart, and a metrics summary table.

#### Scenario: Render CPU scheduling simulation
- **WHEN** the scene `cpu_scheduling_demo` is executed
- **THEN** it renders the Gantt timeline steps, process blocks moving through states, and populates turnaround/weighted-turnaround metrics in the MetricTable

### Requirement: Render Mode Complexity Constraint
The service SHALL limit scene animation steps and maximum rendered items (e.g. nodes, queue sizes, lines of code) according to the configuration's `mode` (`quick`, `standard`, `detailed`).

#### Scenario: Render in quick mode
- **WHEN** `video_config.mode` is set to `quick`
- **THEN** the output resolution is capped at 720p, queue nodes are restricted to 6, and simple transition animations are used to optimize compile times
