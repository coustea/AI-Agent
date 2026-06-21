## 1. Backend Data Source Refactor

- [x] 1.1 Rewrite PPT prompt in `server/app/resource/prompts/ppt.md` to specify `Layout + Slots + Blocks` structure.
- [x] 1.2 Refactor Pydantic models in `server/app/resource/agents/ppt.py` (`PptSlide`, `PptPayload`) to enforce the new `slots` dictionary and layout enumerations.

## 2. Frontend Types & Theme System

- [x] 2.1 Refactor frontend types in `src/features/resource/components/ppt-engine/types/ppt.ts` to include `BaseBlock`, dynamic block interfaces, and the new `SlideData`.
- [x] 2.2 Create CSS Variables theme file `src/features/resource/components/ppt-engine/assets/themes.css`.

## 3. Atomic Blocks Implementation

- [x] 3.1 Create `BlockHeading.vue` component.
- [x] 3.2 Create `BlockText.vue` component.
- [x] 3.3 Create `BlockCallout.vue` component.
- [x] 3.4 Create `BlockCode.vue` component.
- [x] 3.5 Create `BlockBigNumber.vue` component.
- [x] 3.6 Create `BlockFormula.vue` component.
- [x] 3.7 Create `BlockTimeline.vue` component.
- [x] 3.8 Create `BlockTerminal.vue` component.

## 4. Layouts & Renderer Integration

- [x] 4.1 Create `LayoutFocusTitle.vue`.
- [x] 4.2 Create `LayoutSplitScreen.vue`.
- [x] 4.3 Create `LayoutBentoGrid.vue`.
- [x] 4.4 Create `LayoutLayerStack.vue`.
- [x] 4.5 Refactor `PptPlayer.vue` to dynamically mount layouts, pass slots, and apply Vue `<Transition>`.
