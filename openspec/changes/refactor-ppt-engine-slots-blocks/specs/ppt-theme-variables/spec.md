## ADDED Requirements

### Requirement: PPT UI components driven by CSS variables
The frontend blocks and layouts SHALL use CSS variables (e.g., `--ppt-bg-primary`, `--ppt-text-primary`) for all colors and structural styling instead of hardcoded hex values or Tailwind classes.

#### Scenario: Switching from light to dark theme
- **WHEN** the `template_id` changes from `theme-mac-light` to `theme-logic-blue`
- **THEN** the wrapper component's class changes, causing all nested blocks to inherit the new CSS variable values automatically.
