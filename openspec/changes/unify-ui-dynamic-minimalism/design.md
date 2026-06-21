## Context

The current frontend ecosystem is highly fragmented. Although `style.css` defines a robust "Slate & Indigo" token system, `Home.vue`, `Tutor.vue`, and `ResourceGenerator.vue` all implement custom CSS grids, card styles, and heavy inline effects (e.g., intense neon gradients in `ResourceGenerator.vue`, hardcoded HEX backgrounds in `Home.vue`). The goal is to unify these interfaces into a "Dynamic Tactile Minimalism" aesthetic, which relies heavily on whitespace, shared component layout tokens, subtle tactile depth (soft drop shadows, 1px light borders), and progressive disclosure for multi-agent observability.

## Goals / Non-Goals

**Goals:**
- Eliminate hardcoded color values (HEX/RGB) across the main views in favor of CSS variables from `style.css`.
- Extract common structural components (e.g., `<BaseCard>`) into `src/shared/ui` to reduce CSS duplication.
- Redesign `ResourceGenerator.vue` to use standard white-slate cards and glassmorphism, eliminating the heavy gaming-like neon effects.
- Ensure all pages share a uniform, clean background (Slate 50 / `#F8FAFC`).

**Non-Goals:**
- Changing business logic or state management flows (Vuex/Pinia, API integrations).
- Rewriting the digital human avatar logic or backend streaming integrations.
- Adding dark mode support (though using tokens paves the way for this in the future).

## Decisions

**1. CSS Token Enforcement**
- **Rationale**: Rely strictly on `var(--color-bg)` for main layouts, `var(--color-surface)` for cards, and `var(--color-primary)` for key actions. This normalizes the color palette.
- **Alternative**: Ad-hoc SCSS mixing or a new utility-first library like Tailwind. *Rejected* because the existing `style.css` is already robust enough; we just need to enforce it.

**2. Component Extraction (`BaseCard.vue`)**
- **Rationale**: The card pattern is repeated dozens of times with slight variations (`.card`, `.panel`, `.module-panel`, `.dag-node-card`). A `<BaseCard>` component will standardize border radius (`var(--radius-xl)`), border color (`var(--color-border)`), and soft shadows (`var(--shadow-sm)`). It simplifies `Home.vue` and `ResourceGenerator.vue` drastically.

**3. "Dynamic Tactile Minimalism" in Multi-Agent Visualization**
- **Rationale**: `ResourceGenerator.vue` currently uses a massive, complex DAG visualization with glowing `.live-dot` elements. We will refactor this to use clean white cards. When an agent is "active", it will rely on subtle glassmorphism (backdrop-filter) and micro-animations rather than overwhelming neon glows. This maintains a professional EdTech feel.

## Risks / Trade-offs

- [Risk] Heavily refactoring `ResourceGenerator.vue` might break the complex DAG status animations.
  → **Mitigation**: Ensure we only replace CSS classes and layout structures in the template, strictly preserving the reactive `class` bindings and state logic.

- [Risk] Custom overrides on Element Plus components might clash with the new unified `<BaseCard>`.
  → **Mitigation**: We will review and retain necessary Element Plus overrides from `style.css` but move local overrides into the global scope if they represent global patterns (like standardized inputs).
