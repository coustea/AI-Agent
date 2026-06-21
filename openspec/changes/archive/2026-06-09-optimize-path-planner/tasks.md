## 1. Upgrade LearningPathEntry.vue

- [x] 1.1 Replace `entry-copy` and `entry-card` containers with `BaseCard`
- [x] 1.2 Refactor the `<textarea>` to use `BaseInput` type="textarea" (or apply base styling if type="textarea" isn't supported)
- [x] 1.3 Upgrade action buttons (`primary-btn`, `ghost-btn`) to use `<BaseButton variant="primary">` and `<BaseButton variant="secondary">`
- [x] 1.4 Refactor `quickIdeas` tags to use `<BaseTag tone="indigo" interactive>`
- [x] 1.5 Remove unused custom CSS classes (e.g. `.primary-btn`, `.ghost-btn`, `.idea-tag`)

## 2. Upgrade LearningPathOverview.vue

- [x] 2.1 Wrap the `overview-header` in a `BaseCard` with `recommend-bg-decoration`
- [x] 2.2 Upgrade action buttons in the header to `<BaseButton>`
- [x] 2.3 Refactor the `summary-grid` panels to use `BaseCard`
- [x] 2.4 Refactor the progress bar to use global design tokens (e.g. `--color-primary`)
- [x] 2.5 Refactor `stage-panel` layouts and typography to align with global design
- [x] 2.6 Upgrade `node-card` elements to `<BaseCard hoverable>` instead of `<button class="node-card">`
- [x] 2.7 Replace node status text labels with `<BaseTag pill>` using contextual tones (e.g., emerald for completed, indigo for available)
- [x] 2.8 Remove unused custom CSS classes

## 3. Verification & Polish

- [x] 3.1 Verify UI layout and responsiveness on `/path-planner` and `/path-planner/overview/latest`
- [x] 3.2 Ensure clicking nodes properly navigates and click bubbling behaves correctly
- [x] 3.3 Ensure there are no accessibility issues with replacing native buttons with interactive cards
