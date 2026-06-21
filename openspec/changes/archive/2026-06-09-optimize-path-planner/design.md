## Context

The UI components in the Learning Path planner views are currently built with raw HTML and custom CSS styles (e.g. `<button class="primary-btn">`, `<textarea>`). We are transitioning these to use the new atomic components (`BaseCard`, `BaseButton`, `BaseInput`, `BaseTag`) to conform with the "Dynamic Tactile Minimalism" design system.

## Goals / Non-Goals

**Goals:**
- Upgrade `LearningPathEntry.vue` and `LearningPathOverview.vue` to use the unified component library.
- Improve component interactivity (hover, active states) while reducing raw CSS.
- Ensure the layout degrades gracefully on mobile views.

**Non-Goals:**
- No changes to backend API integrations.
- No changes to the underlying path generation logic or state management.

## Decisions

- **UI Component Upgrades**: 
  - Standard `<button>` elements will be replaced with `<BaseButton>`.
  - Content containers and summary panels will be wrapped in `<BaseCard>`.
  - The text area in `LearningPathEntry` will be upgraded to use the global input styling.
  - Interactive "node cards" in `LearningPathOverview` will utilize `<BaseCard hoverable>`.
  - Node statuses will be represented using `<BaseTag pill>`.

## Risks / Trade-offs

- **Risk**: Potential layout breakage due to component structural differences (e.g., `BaseButton` padding overriding custom sizes).
  - **Mitigation**: Rely on utility classes or localized flex layout wrappers instead of rigid fixed widths/heights, and test responsive breakpoints extensively.
