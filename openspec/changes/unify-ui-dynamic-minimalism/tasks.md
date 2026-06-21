## 1. Setup Common UI Components

- [x] 1.1 Create `src/shared/ui/BaseCard.vue` to encapsulate the card style (`var(--color-surface)`, `var(--radius-xl)`, `var(--color-border)`, soft drop shadow).

## 2. Refactor Home View

- [x] 2.1 Refactor `src/features/dashboard/views/Home.vue` to replace custom `.card` and `.modules-card` implementations with `<BaseCard>`.
- [x] 2.2 Remove all hardcoded HEX colors (e.g. `#F8FAFC`, `#FFFFFF`) from `Home.vue` scoped CSS and use global CSS variables (`var(--color-bg)`, `var(--color-surface)`).

## 3. Refactor Tutor View

- [x] 3.1 Update `src/features/chat/views/Tutor.vue` to replace custom sidebar and container backgrounds with `var(--color-surface)` and `var(--color-bg)`.
- [x] 3.2 Ensure the floating FAB menu and digital human status overlay use proper glassmorphism (backdrop-filter) and tactile depth instead of flat backgrounds.

## 4. Refactor Resource Generator View

- [x] 4.1 Remove heavy neon glowing backgrounds (`.omni-ambient-bg`, `.glow-blue`) from `src/features/resource/views/ResourceGenerator.vue`.
- [x] 4.2 Replace the `personalize-view` panels and `results-view` bento grid cards with the new `<BaseCard>`.
- [x] 4.3 Redesign the DAG multi-agent execution nodes (`.dag-node-card`) to use clean slate/white cards with subtle borders and clear state indicators instead of glowing dots.
