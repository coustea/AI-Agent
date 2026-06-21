## ADDED Requirements

### Requirement: AI Backend specifies explicit layout and slots
The PPT Agent SHALL return a JSON schema where each slide contains a `layout` identifier and a `slots` map containing arrays of blocks.

#### Scenario: Valid slide JSON output
- **WHEN** the backend generates a PPT slide
- **THEN** it outputs a layout string (e.g., 'SplitScreen') and slots (e.g., left, right) filled with blocks with `type` and content.

### Requirement: Frontend dynamic rendering of layouts and blocks
The frontend `PptPlayer.vue` SHALL dynamically render layouts and atomic blocks based on the data schema.

#### Scenario: Rendering SplitScreen layout
- **WHEN** the frontend receives a `SplitScreen` layout with a `Code` block in the right slot
- **THEN** it renders `LayoutSplitScreen.vue` and places a `BlockCode.vue` component inside the right slot area.
