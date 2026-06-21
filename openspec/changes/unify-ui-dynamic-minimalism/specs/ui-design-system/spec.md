## ADDED Requirements

### Requirement: Unified Base Layout System
The system SHALL use a centralized base layout structure for all primary views to ensure visual consistency.

#### Scenario: Rendering Home Dashboard
- **WHEN** the user navigates to the Home dashboard
- **THEN** the layout is rendered using the standard `var(--color-bg)` background, and all widget panels are instantiated via the shared `<BaseCard>` component with consistent border radii and tactile drop shadows.

### Requirement: Standardized Multi-Agent Visualization
The system SHALL present multi-agent activity using the "Dynamic Tactile Minimalism" style, avoiding high-contrast neon glows in favor of subtle glassmorphism and clear state indicators.

#### Scenario: Generating a Resource
- **WHEN** the user initiates the AI Resource Generator
- **THEN** active agents are displayed using clean slate/white cards with subtle blur effects (backdrop-filter) and spinning micro-animations, while inactive agents remain visually subdued.

### Requirement: Elimination of Hardcoded Colors
The system SHALL enforce the usage of CSS variables defined in `style.css` across all feature views, completely eliminating raw HEX or RGB color codes in component-scoped styles for structural elements.

#### Scenario: Inspecting the Tutor UI
- **WHEN** the Tutor chat interface is rendered
- **THEN** the chat bubbles, sidebar, and input panels use `var(--color-surface)` and `var(--color-primary-soft)` instead of ad-hoc color values.
