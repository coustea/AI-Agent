## Why

The current frontend suffers from visual fragmentation across different pages (e.g., Home, Tutor, Resource Generator). Each page feels like a separate product due to inconsistent backgrounds, card styles, and heavy inline CSS. Unifying the UI into a "Dynamic Tactile Minimalism" style will provide a consistent, immersive, and professional experience suitable for an AI-powered personalized learning platform, reducing cognitive load and easing future maintenance.

## What Changes

- Extract and implement a shared design system with fundamental UI components (e.g., `BaseCard`, `PageLayout`).
- Standardize the color palette to strictly adhere to the Indigo/Slate tokens defined in `style.css`.
- Refactor `Home.vue` to use standard cards and remove hardcoded colors.
- Refactor `ResourceGenerator.vue` to tone down excessive neon glows, replacing them with subtle glassmorphism and tactile depth, aligning with the "Dynamic Tactile Minimalism" theme.
- Refactor `Tutor.vue` to use the unified background colors, standardized agent cards, and progressive disclosure for agent observability.

## Capabilities

### New Capabilities
- `ui-design-system`: Defines the core design language, shared UI components, and visual rules (Dynamic Tactile Minimalism) for the entire platform.

### Modified Capabilities
<!-- No requirement changes to existing features, only UI layer refactoring. -->

## Impact

- **Affected Code**: Frontend views (`Home.vue`, `Tutor.vue`, `ResourceGenerator.vue`), global styles (`style.css`), and the new `src/shared/ui/` component library.
- **Dependencies**: No new external dependencies required, but will heavily utilize Element Plus with custom overrides.
