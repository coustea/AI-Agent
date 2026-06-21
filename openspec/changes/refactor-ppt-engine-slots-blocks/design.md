## Context

The current AI generated PPT system returns a rigid structure where each `slide` maps precisely to a predefined theme template (e.g., `<TheoryProofSlide :data="data" />`). This prevents the AI from dynamically mixing content types and tightly couples the backend schema to the frontend view structure. 

## Goals / Non-Goals

**Goals:**
- Decouple layout structural definitions from visual styling by using a slot-based layout system with CSS Variables for themes.
- Define a generic schema allowing the AI to specify a layout (e.g., SplitScreen) and independently place blocks (e.g., Heading, Text, Code) into designated slots.
- Ensure backwards compatibility in capabilities (support code highlighting, theory proofs, terminal outputs) by providing equivalent atomic blocks.

**Non-Goals:**
- We are not changing the core `PptPlayer` state management or presentation mechanics (like slide transitions and speaker notes), just the rendering loop.
- We will not implement a visual drag-and-drop editor for users; this is strictly an AI-to-Frontend rendering pipeline refactor.

## Decisions

- **Architecture:** We will use a Slot and Block architecture. A slide defines a `layout` string and a dictionary of `slots`, where each slot contains an array of `Blocks`.
- **Backend changes:** We will update `PptPayload` and `PptSlide` Pydantic models in `server/app/resource/agents/ppt.py` to enforce the new schema. We will rewrite the prompt at `server/app/resource/prompts/ppt.md` to guide the model.
- **Frontend changes:** In `ppt-engine`, we will replace `themes/` with `layouts/` (e.g., `LayoutSplitScreen.vue`) and `blocks/` (e.g., `BlockHeading.vue`). 
- **Theming:** We will use CSS Variables applied at the `.ppt-player-container` level depending on the selected `template_id` (e.g., `theme-logic-blue`).

## Risks / Trade-offs

- **[Risk] Model Adherence**: The AI may struggle to output nested slot structures correctly compared to the previous flat structure.
  - *Mitigation*: We will provide a very detailed JSON schema example in the prompt and use JSON Mode / Structured Output features where possible.
- **[Risk] Animation Jitter**: Transitioning between dynamically loaded layout components could cause layout shifts.
  - *Mitigation*: We will use Vue's `<Transition name="slide-fade" mode="out-in">` explicitly on the layout wrapper.
