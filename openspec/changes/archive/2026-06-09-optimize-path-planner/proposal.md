## Why

The Learning Path Planner pages (`LearningPathEntry.vue` and `LearningPathOverview.vue`) currently use legacy HTML structures and hard-coded custom CSS styles (e.g., raw `<button>`, `#2563eb`). This creates a visual and interaction disconnect with the newly unified "Dynamic Tactile Minimalism" aesthetic that has been rolled out to the Home, Tutor, and Resource Generator pages. Unifying these pages will complete the frontend style alignment, providing a cohesive premium feel and tactile feedback across all major touchpoints.

## What Changes

- Refactor `LearningPathEntry.vue` to use `BaseCard`, `BaseButton`, `BaseInput` and `BaseTag`.
- Refactor `LearningPathOverview.vue` to use `BaseCard` for the hero section and overview grids.
- Upgrade the interactive node list in `LearningPathOverview.vue` to use `<BaseCard hoverable>` for nodes and `<BaseTag pill>` for status chips.
- Remove redundant legacy CSS classes (`.primary-btn`, `.ghost-btn`, `.idea-tag`) in favor of global styles and `Base*` components.
- Ensure responsive layouts degrade gracefully on mobile screens.

## Capabilities

### New Capabilities
*(None)*

### Modified Capabilities
*(None)*

## Impact

- **Affected files**: 
  - `src/features/learning/views/LearningPathEntry.vue`
  - `src/features/learning/views/LearningPathOverview.vue`
- **Dependencies**: Relies on existing atomic components `BaseCard`, `BaseButton`, `BaseInput`, `BaseTag`.
