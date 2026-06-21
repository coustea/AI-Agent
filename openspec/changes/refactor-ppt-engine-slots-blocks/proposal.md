## Why

The current PPT generation and rendering engine relies on a flat data structure and hard-coded layout templates (e.g., MixedTwoColumn). This creates a rigid "fill-in-the-blanks" architecture that severely limits the layout flexibility and dynamic expressiveness of the generated presentations. Moving to a Data-Driven Slot & Block Architecture allows the AI to compose pages dynamically and provides the frontend with completely decoupled styling and structural components.

## What Changes

- Transition the AI-generated JSON schema from flat slide data to a `Layout -> Slots -> Blocks` hierarchy.
- Rebuild the frontend TypeScript definitions (`types/ppt.ts`) to support dynamic base blocks and layouts.
- Create atomic presentation components (e.g., `BlockHeading`, `BlockCallout`, `BlockCode`) using CSS Variables.
- Replace static slide themes with universal layout containers (e.g., `LayoutSplitScreen`, `LayoutBentoGrid`).
- Refactor the core engine `PptPlayer.vue` to dynamically resolve layouts and blocks using Vue's `<component :is="...">`.
- **BREAKING**: The backend AI `PptPayload` schema will change, requiring frontend/backend synchronous updates.

## Capabilities

### New Capabilities
- `ppt-slot-block-architecture`: Introduction of the composable slot and block layout engine for PPTs.
- `ppt-theme-variables`: A new CSS Variable-based theme system separating design tokens from component structure.

### Modified Capabilities

## Impact

- **Backend API & Agents**: Modifies the prompts and Pydantic validation schemas in `server/app/resource/prompts/ppt.md` and `server/app/resource/agents/ppt.py`.
- **Frontend Components**: Extensively refactors `src/features/resource/components/ppt-engine/`, replacing `themes/` with `layouts/` and `blocks/`.
- **Frontend Core**: Significant rewrites to `ppt.ts` and `PptPlayer.vue`.
