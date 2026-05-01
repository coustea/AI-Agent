# Multi-Agent Resource Generator UI Redesign Spec

## 1. Overview
The goal of this redesign is to strongly emphasize the "Multi-Agent" architecture to users when generating personalized learning resources. The current `ResourceGenerator.vue` page will be rebuilt to eliminate long blank screens by surfacing real-time agent execution progress and streaming multimodal content into a dynamic "Bento Box" grid. 

This design will also address minor accessibility and CSS performance issues identified by Vercel's Web Interface Guidelines (e.g., missing `<label>` associations, replacing `transition: all`).

## 2. Layout Architecture: Split View
The page will adopt a side-by-side (Split View) layout to balance configuration inputs and real-time outputs.

### Left Panel: Chat & Personalized Configuration (Input)
A persistent configuration and chat-like panel where the student provides their learning context.

- **Course Information Form:** 
  - Fields: Course, Chapter (optional), Topic (Required), Knowledge Weak Points (Tags input).
  - Explicit `<label>` to `id` connections (`htmlFor` equivalent) for all form inputs.
- **Personalized Preferences:**
  - Learning Goal, Current Level, Target Level, Explanation Style, Content Depth.
- **Agent Orchestration Config (Simplified):**
  - Switches to enable/disable specific agents (Content, Diagram, Mindmap, Quiz, Reading, Code).
  - A hidden/drawer configuration for deeper agent settings (e.g., diagram type, question count) to keep the primary UI clean.
- **Action Area:**
  - A prominent "Generate Personalized Resources" button.
  - A dynamic summary text box that updates as the user fills out the form.

### Right Panel: Multi-Agent Bento Workspace (Output)
A dynamic canvas that visualizes the AI workflow and displays the final resources.

- **Workflow Timeline / Activity Feed (Top):**
  - A compact horizontal or vertical timeline showing the current execution stage of the LangGraph/Coordinator agent.
  - Displays real-time SSE logs (e.g., "ContentAgent is writing explanation...", "MindmapAgent is structuring knowledge...").
  - An overall progress bar (0-100%).
- **Bento Box Grid (Main Area):**
  - A responsive CSS Grid containing individual "cards" or "tiles" for each active agent.
  - **Tile States:**
    - *Pending:* Dimmed, waiting for dependencies.
    - *Running:* Active skeleton loader, pulse animation, or partial streaming text (if supported by SSE payload).
    - *Success:* Displays a rich preview of the generated artifact (Markdown snippet, Mermaid diagram render, Quiz JSON preview, Code snippet).
    - *Failed:* Clear error state with an option to retry.
  - **Component Re-use:** We will reuse the existing `MarkdownResourceView`, `MindmapResourceView`, `DiagramResourceView`, and `QuizResourceView` components within these tiles, leveraging their `compact` mode for the grid view.
- **Action Footer (Bottom/Overlay):**
  - Buttons to "View Full Screen" for specific resources or "Download Entire Bundle".

## 3. Interaction & Streaming Feedback
To avoid long blank screens, the frontend will actively parse the SSE stream from `POST /generate`:
1. **`workflow` events:** Update the top timeline and overall progress bar.
2. **`agent` events:** Transition the corresponding Bento tile from "Pending" to "Running". Display status messages inside the tile (e.g., "Drawing flowchart...").
3. **`resource` events:** Transition the tile to "Success" and inject the JSON/Markdown payload into the specific ResourceView component.
4. **`review` & `bundle` events:** Display final quality scores or learning path suggestions in a dedicated summary tile.

## 4. Web Interface Guidelines Fixes
During the redesign, the following specific compliance issues will be resolved:
- **`ResourceGenerator.vue`**:
  - Add `aria-live="polite"` to the dynamic summary box (`.dynamic-summary-box`).
  - Add explicit `id` attributes to all `<el-input>` and `<el-select>` elements and bind their `<label>` elements using `for="id"`.
  - Replace `transition: all` in CSS with explicit properties (e.g., `transition: transform 0.2s ease, border-color 0.2s ease, box-shadow 0.2s ease;`).
- **`ResourceCard.vue`**:
  - Fix typographic ellipsis (replace `...` with `…`).
  - Add `alt=""` to `<el-image>` components.
  - Add `aria-hidden="true"` to decorative `<el-icon>` components.
- **`QuizResourceView.vue`**:
  - Ensure `v-for` loops use a unique `question.id` or reliable identifier for the `:key` instead of just the array `index` where possible (or ensure the array is static if using index).

## 5. Implementation Plan
1. **Refactor Components:** Update `ResourceCard.vue` and `*ResourceView.vue` components to fix guideline issues and ensure they render perfectly inside a CSS Grid context.
2. **Rebuild `ResourceGenerator.vue`:**
   - Implement the two-column CSS layout.
   - Wire up the form inputs with proper accessibility tags.
   - Build the Workflow Timeline component to react to SSE state.
   - Build the Bento Grid component mapped to the `workflow.states` and `generatedResources` reactive data.
3. **Wire SSE Logic:** Ensure the existing `generateResources` SSE callback correctly updates the new grid tiles without wiping state.
4. **Self-Review:** Test the layout for responsiveness and verify that the "blank screen" problem is solved by the new loading states.