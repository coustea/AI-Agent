## ADDED Requirements

### Requirement: Linear chat execution pipeline
The chat system SHALL execute each tutoring turn as a linear pipeline that evaluates the request, optionally analyzes attachments, optionally gathers search context, produces a unified answer, and optionally generates a teaching diagram after the answer is complete.

#### Scenario: Turn with attachments and web search enabled
- **WHEN** a user sends a tutoring message with attachments and web search enabled
- **THEN** the system SHALL analyze the attachments before generating the final answer
- **THEN** the system SHALL gather search context before generating the final answer
- **THEN** the system SHALL generate one unified answer after both preparation steps finish

#### Scenario: Turn without attachments or search
- **WHEN** a user sends a tutoring message without attachments and without search requirements
- **THEN** the system SHALL skip attachment analysis and search preparation
- **THEN** the system SHALL proceed directly to the unified answer stage

### Requirement: Shared state for preparation results
The chat agent SHALL store attachment analysis results and search preparation results in shared runtime state so that later stages can consume them without recomputing or re-fetching the same data.

#### Scenario: Answer consumes attachment analysis result
- **WHEN** attachment analysis completes successfully
- **THEN** the runtime state SHALL persist an attachment analysis context for the answer stage
- **THEN** the answer stage SHALL use that stored context instead of re-analyzing the same attachments

#### Scenario: Answer consumes search result
- **WHEN** search preparation completes successfully
- **THEN** the runtime state SHALL persist the search result and source metadata for the answer stage
- **THEN** the answer stage SHALL use that stored result as external evidence for the final answer

### Requirement: On-demand learner context tools
The chat answer stage SHALL NOT preload learner profile or long-term memory into every turn by default, and SHALL instead allow the agent to retrieve those contexts on demand through tools when the current turn requires them.

#### Scenario: General factual tutoring question
- **WHEN** the current turn can be answered from the user message, conversation context, attachment analysis, and search context
- **THEN** the system SHALL allow the answer stage to complete without retrieving learner profile or long-term memory

#### Scenario: Personalized tutoring continuation
- **WHEN** the current turn requires prior learner preferences, stable weak points, or cross-session tutoring continuity
- **THEN** the answer stage SHALL be able to call tools that retrieve learner profile and long-term memory during generation

### Requirement: Unified answer stage
The chat system SHALL use a single answer stage to generate the final tutoring response for both attachment-assisted turns and non-attachment turns.

#### Scenario: Attachment-assisted answer
- **WHEN** attachment analysis context exists in runtime state
- **THEN** the answer stage SHALL prioritize that attachment context when explaining the user question
- **THEN** the answer stage MAY combine it with search context or on-demand tools if additional evidence is needed

#### Scenario: Plain tutoring answer
- **WHEN** no attachment analysis context exists in runtime state
- **THEN** the same answer stage SHALL generate the tutoring response using the available conversation and search context

### Requirement: Post-answer teaching diagram generation
The chat system SHALL generate teaching diagrams only after a final text answer exists and only when the current turn requests diagram output.

#### Scenario: Diagram requested
- **WHEN** a tutoring turn requests a teaching diagram and the answer stage completes successfully
- **THEN** the system SHALL generate the diagram after the final answer text is available

#### Scenario: Diagram not requested
- **WHEN** a tutoring turn does not request a teaching diagram
- **THEN** the system SHALL end the turn after the final answer stage without running diagram generation
