# Chat Video and Diagram Output Design

## Goal

Align the existing Vue chat page and FastAPI chat runtime so that video and
diagram generation are explicit output modes with predictable message
placement:

- Video generation starts only after the learner selects Video and presses
  Send.
- A video turn never starts TutorAgent and never creates a text answer.
- Video waiting, success, and failure states appear as an AI artifact row on
  the left, immediately after the learner's topic on the right.
- An explicitly selected Diagram turn produces only a diagram.
- In ordinary chat, TutorAgent may autonomously generate a diagram when the
  learner asks for one or a visual explanation materially helps.
- Any successful diagram generation ends the turn without a text answer.

The visual treatment must reuse the current `Tutor.vue` message layout,
avatar, composer, width constraints, and design tokens. It must not introduce
a detached page or a second chat presentation.

## Scope

Included:

- Standard chat composer mode selection for Video and Diagram.
- Existing chat video API submission and polling.
- Left-side derived AI video artifact rendering.
- Video polling cancellation, bounded failure handling, and terminal-state
  validation.
- A typed teaching-diagram TutorAgent tool.
- `diagram_mode: "auto" | "required"` across the HTTP, service, and agent
  boundaries.
- Diagram-only streaming completion and persistence.
- History restoration for repeated video topics and empty-text diagram
  assistant messages.
- Focused frontend and backend regression tests.

Excluded:

- Exposing video generation as a TutorAgent tool.
- Creating a second diagram HTTP lifecycle.
- Changing the shared cartoon rendering pipeline.
- Redesigning the chat page or digital-human experience.
- Persisting a synthetic assistant video message.

## Options Considered

### 1. Independent video API plus diagram Agent Tool (selected)

Keep video generation behind the existing explicit `/chat/videos` API and
polling flow. Render its artifact as a derived AI row while keeping persistence
on the source user message. Add a typed diagram tool to TutorAgent, with
`required` forcing one direct tool execution and `auto` allowing an Agent
decision.

This preserves the current persistence model, prevents accidental video
generation, supports autonomous diagrams, and provides one diagram path for
both explicit and Agent-selected generation.

### 2. Independent APIs for both video and diagram

An explicit diagram endpoint would make selected generation independent from
TutorAgent, but autonomous diagrams would still require a Tool. The frontend
would then own two diagram lifecycles, two error paths, and reconciliation
between endpoint-generated and Agent-generated history. The added boundary
does not provide enough value for this feature.

### 3. Prompt tags and synthetic assistant messages

The model could continue emitting standalone `<diagram>` JSON, and the
frontend could insert fake AI video messages. This has the smallest apparent
diff but is fragile: malformed tags need repair, tool intent is implicit,
diagram-only output conflicts with the existing answer parser, and synthetic
AI rows interfere with code that treats the latest AI message as the active
answer. This option is rejected.

## Frontend Interaction

The standard composer owns a single output selection:

- No selected artifact: ordinary chat, sent with `diagram_mode=auto`.
- Diagram selected: the Diagram button is active; Send starts a required
  diagram-only chat turn.
- Video selected: the Video button is active; Send starts the independent
  video task and does not start the chat SSE flow.

Diagram and Video are mutually exclusive. Clicking an active artifact button
returns to ordinary chat. Video selection is disabled while attachments are
present because the video API accepts a topic only. After a video submission,
the Video selection resets so a later Send cannot accidentally generate
another video. The learner's typed topic remains the source user message.

The existing Send button remains the only command that submits the composer.
Clicking Video no longer performs a network request.

## Video Rendering and State

Backend persistence remains unchanged: the video payload stays in the user
message's `usage_metadata.video`, and polling continues to use the persisted
user message ID.

`Tutor.vue` renders that single record as two adjacent visual rows:

1. The normal learner message on the right, containing the topic.
2. A derived `.message-row.ai` on the left, keyed by
   `${message.id}:video`, containing the normal AI avatar, metadata, and
   `ChatVideoArtifact`.

The derived row is a rendering projection only. It is not inserted into the
`messages` array and is not persisted. This avoids confusing answer streaming,
diagram event routing, and history recovery code that searches for the latest
AI message.

The artifact has four renderable outcomes:

- `queued` or `running`: show the compact waiting animation.
- `completed` with `video_url`: replace the waiting state in place with the
  player.
- `failed`: show the backend `error` text when available.
- `completed` without `video_url`: show a terminal invalid-result error; never
  keep displaying the waiting animation.

Animation respects `prefers-reduced-motion: reduce`.

## Video Polling Reliability

`useChatVideoTasks` owns an increasing generation token. `dispose()` advances
the token and clears timers; an in-flight request must compare its captured
token before invoking callbacks or scheduling another poll. Session switch,
new session, and component unmount all dispose current video watchers.

Transient poll failures retry only up to a fixed consecutive-failure limit.
After the limit, the composable emits a local failed artifact containing a
clear retry message and stops polling. A successful response resets the
failure count. Terminal server states always stop polling.

History deduplication uses persisted message IDs when available. Content-based
deduplication is only a fallback for records without stable IDs, so two video
requests with the same topic remain separate turns.

## Diagram Request Contract

The canonical request field is:

```text
diagram_mode: "auto" | "required"
```

Semantics:

- `required`: the learner selected Diagram. The backend invokes the teaching
  diagram tool exactly once without running the text-answer LLM path.
- `auto`: the ordinary TutorAgent path. TutorAgent may invoke the diagram tool
  when the learner explicitly asks for a diagram or when a visual explanation
  is instructionally useful.

During migration, the HTTP route accepts the existing
`need_teaching_diagram` field as a compatibility alias:

- `true` maps to `required`.
- `false` maps to `auto`.
- An explicit valid `diagram_mode` takes precedence.

The frontend sends the canonical field. Internal schemas, state, and functions
use `diagram_mode`; compatibility is contained at the HTTP boundary.

## Diagram Tool Boundary

`build_tutor_tools` adds a typed `generate_teaching_diagram` tool. Its input is
the current teaching question plus the minimum context needed to produce a
correct visual explanation. Its handler calls the existing structured diagram
generator and returns the validated diagram payload. The tool is unavailable
to unrelated agents.

`ToolExecutionResult` exposes the structured `result_payload` directly so the
ReAct node does not reach into invocation serialization details.

Execution behavior:

- In `required`, the node calls the tool directly, validates the payload, and
  returns `final_answer=""` plus `diagram_result`.
- In `auto`, TutorAgent may call the tool through the normal tool-call path.
  A successful diagram payload terminates the loop immediately and returns no
  answer tokens.
- A diagram-tool failure terminates a required turn with a real error. It does
  not fall back to a text answer.
- In auto mode, choosing the diagram tool commits the turn to diagram output.
  A failed call terminates through the existing tool activity/error path and
  does not fall back to a text answer.

The Tutor prompt describes when to call the tool. It no longer requests
standalone `<diagram>` JSON, no longer forbids autonomous visual explanations,
and retains `<answer>` only for ordinary text answers.

## Diagram Streaming and Persistence

A turn is successful when either condition is true:

```python
bool(full_answer.strip()) or diagram_result is not None
```

For diagram-only success, the service:

- emits `diagram.ready` before `message.completed`;
- does not emit answer tokens or `content_replace`;
- saves one assistant message with `content=[]`;
- stores the delivered diagram in `usage_metadata.diagram`;
- returns `saved_message_id` in the done payload;
- skips text-dependent long-term memory jobs.

History already projects assistant diagram metadata. The frontend must retain
an assistant row with empty text when it contains a diagram, so refresh restores
the same diagram-only result.

PNG rendering remains part of delivery. A structured fallback diagram is a
valid artifact when image rendering fails, following the current retry model.

## Error Handling

- Invalid `diagram_mode` returns HTTP 422 through FastAPI form validation.
- Empty video topics keep the existing HTTP 400 response.
- Video creation errors update the derived AI artifact to `failed` with the
  returned message.
- Poll exhaustion produces a terminal local failure rather than an infinite
  animation.
- Required diagram generation failure produces the existing failed stream
  state and no assistant success message.
- Diagram-only persistence failure reports stream failure; the UI must not
  treat the earlier diagram event as a saved completed turn.

## Verification

Backend tests must prove:

- The API maps legacy diagram booleans and accepts canonical modes.
- Required mode invokes the diagram tool once and never calls the text-answer
  LLM or emits `answer_token`.
- Auto mode can terminate after a successful diagram tool call with no text.
- Ordinary auto mode still produces a text answer when no diagram is selected.
- Empty answer plus diagram persists an assistant message with empty content,
  diagram metadata, and a saved message ID.
- Diagram-only success emits no `content_replace` and schedules no text memory
  job.
- Diagram failure does not silently become a text answer.
- Prompt contract tests reject the old standalone `<diagram>` protocol.

Frontend tests must prove:

- The video artifact distinguishes waiting, failed, valid completed, and
  invalid completed states.
- Failed state displays `video.error`.
- Reduced-motion CSS disables the waiting animation.
- Video polling cannot restart after disposal and stops after bounded errors.
- Stable-ID history dedup preserves repeated equal-topic video messages.

Final validation runs focused chat tests, the complete frontend test command,
the frontend production build, and a browser check of the real Tutor page at
desktop and mobile widths. The visual check confirms the topic is on the right,
the waiting/player artifact is on the left, no synthetic text answer appears,
and no controls overlap.
