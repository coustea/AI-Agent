# Onboarding Dialog Redesign Implementation Plan (Glacier Teal & Panels Layout)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Redesign the onboarding dialog to have 100% zero rounded corners, replacing the legacy "cards-inside-a-card" layout with a clean, flat "panels and vertical dividers" layout aligned with the Glacier Teal style.

**Architecture:** 
1. Remove all borders, backgrounds, and shadows from `.step-rail`, `.chat-card`, and `.profile-panel`.
2. Set `.onboarding-workspace` to have `gap: 0` and make it flush with the main container. Add a top border to separate the workspace from the header.
3. Add vertical border dividers: a right border on `.step-rail` and a right border on `.chat-card` (separating them from `.chat-card` and `.profile-panel`, respectively).
4. Remove rounded corners (`border-radius: 0px`) on all elements including bubbles, avatars, buttons, progress badges, skip buttons, and dropdowns.
5. Replace the circular progress ring with a horizontal rectangular progress bar inside the right panel.

**Tech Stack:** Vue 3, TypeScript, Tailwind v4, CSS.

---

### Task 1: Zero Rounded Corners and Panel Layout Re-Alignment

**Files:**
- Modify: `src/features/auth/components/OnboardingDialog.vue`

- [ ] **Step 1: Update main container to remove rounded corners**

Modify `.onboarding-container` in CSS (around line 1229):
```css
.onboarding-container {
  position: relative;
  width: min(1240px, calc(100vw - 40px));
  height: min(760px, calc(100dvh - 72px));
  max-height: calc(100dvh - 72px);
  display: grid;
  grid-template-rows: auto minmax(0, 1fr);
  overflow: hidden;
  border: 1px solid rgba(159, 220, 218, 0.58);
  border-radius: 0px; /* zero rounded corners */
  background:
      linear-gradient(180deg, rgba(255, 255, 255, 0.99), rgba(247, 253, 252, 0.98)),
      #ffffff;
  box-shadow:
      0 40px 100px rgba(10, 15, 35, 0.26),
      0 8px 32px rgba(20, 184, 166, 0.12),
      0 1px 0 rgba(255, 255, 255, 0.95) inset;
}
```

- [ ] **Step 2: Update workspace to be a seamless panel layout**

Modify `.onboarding-workspace` to remove gap and margins, and add top border (around line 1383):
```css
.onboarding-workspace {
  position: relative;
  z-index: 1;
  min-height: 0;
  display: grid;
  grid-template-columns: 160px minmax(0, 1fr) 230px;
  gap: 0px; /* no gaps between panels */
  margin: 0px; /* flush with container edges */
  border-top: 1px solid rgba(190, 230, 229, 0.74); /* top panel boundary */
}
```

- [ ] **Step 3: Redesign `.step-rail` as a sidebar panel with a vertical divider**

Modify `.step-rail` CSS (around line 1393):
```css
.step-rail {
  padding: 16px 12px;
  min-height: 0;
  overflow: hidden;
  border-radius: 0px;
  background: rgba(255, 255, 255, 0.45);
  border: none;
  border-right: 1px solid rgba(190, 230, 229, 0.74); /* vertical divider */
  box-shadow: none;
  backdrop-filter: blur(18px);
}
```
And make sure step navigation items (`.step-rail-title`, `.step-item`, `.step-index`) have `border-radius: 0px`.

- [ ] **Step 4: Redesign `.chat-card` as a center panel with a vertical divider**

Modify `.chat-card` CSS (around line 1500):
```css
.chat-card {
  position: relative;
  z-index: 1;
  min-height: 0;
  display: grid;
  grid-template-rows: auto minmax(0, 1fr) auto;
  margin: 0;
  overflow: hidden;
  border: none;
  border-right: 1px solid rgba(190, 230, 229, 0.74); /* vertical divider */
  border-radius: 0px;
  background: rgba(255, 255, 255, 0.86);
  box-shadow: none;
  backdrop-filter: blur(18px);
}
```

- [ ] **Step 5: Redesign `.profile-panel` as a right sidebar panel**

Modify `.profile-panel` CSS (around line 2022):
```css
.profile-panel {
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding: 16px 20px;
  overflow-y: auto;
  min-height: 0;
  border: none;
  border-radius: 0px;
  background: rgba(255, 255, 255, 0.45);
  box-shadow: none;
  backdrop-filter: blur(18px);
}
```

- [ ] **Step 6: Remove rounded corners on progress badge, skip button, and title marks**

Ensure the following are updated:
```css
.progress-badge {
  border-radius: 0px;
}
.skip-btn {
  border-radius: 0px;
}
.title-mark span:first-child,
.title-mark span:last-child {
  border-radius: 0px;
}
```

- [ ] **Step 7: Verify and Commit**

Run `npm run build` and commit:
```bash
git add src/features/auth/components/OnboardingDialog.vue
git commit -m "style: implement seamless panel layout and zero rounded corners on panels"
```

---

### Task 2: Redesign Dialogue Bubbles, Avatars, Buttons, and Progress Bar

**Files:**
- Modify: `src/features/auth/components/OnboardingDialog.vue`

- [ ] **Step 1: Set message bubbles and avatars to be sharp rectangles**

Update the CSS for `.message-bubble`, `.avatar-icon`, `.user-avatar` to remove rounded corners:
```css
.avatar-icon,
.user-avatar {
  border-radius: 0px; /* zero rounded corners */
}
.message-bubble {
  border-radius: 0px; /* zero rounded corners */
}
.message-row.assistant .message-bubble {
  border-top-left-radius: 0px;
  border-left: 3px solid var(--color-primary); /* Left accent bar for AI bubble */
}
.message-row.user .message-bubble {
  border-top-right-radius: 0px;
}
```

- [ ] **Step 2: Update quick reply buttons and confirm selection buttons to be sharp blocks**

Remove rounded corners on `.quick-reply-btn` and `.confirm-selection-btn`:
```css
.quick-reply-btn {
  border-radius: 0px; /* zero rounded corners */
}
.confirm-selection-btn {
  border-radius: 0px; /* zero rounded corners */
}
```

- [ ] **Step 3: Replace circular progress ring with a horizontal rectangular progress bar**

Style `.progress-ring` in CSS to act as a horizontal progress bar (around line 2058):
```css
.progress-ring {
  --progress: 0;
  position: relative;
  width: 100%;
  height: 28px;
  border: 1px solid rgba(183, 226, 224, 0.9);
  background: #f8fafc;
  border-radius: 0px; /* zero rounded corners */
  overflow: hidden;
  box-shadow:
      0 4px 12px rgba(20, 160, 157, 0.06),
      inset 0 0 0 1px rgba(255, 255, 255, 0.92);
}
.progress-ring::after {
  content: '';
  position: absolute;
  left: 0;
  top: 0;
  bottom: 0;
  width: calc(var(--progress) * 1%);
  background: linear-gradient(90deg, var(--color-primary), var(--color-action));
  transition: width 0.3s ease;
}
.progress-ring span {
  position: relative;
  z-index: 2;
  color: var(--color-primary-text);
  font-size: 12px;
  font-weight: 950;
  margin: auto;
  display: block;
  text-align: center;
  line-height: 24px;
}
```

- [ ] **Step 4: Update other controls, inputs, suggestions popover, and notes to be sharp**

Ensure no rounded corners on:
```css
.composer-wrapper {
  border-radius: 0px;
}
.send-btn {
  border-radius: 0px;
}
.school-autocomplete-popover {
  border-radius: 0px;
}
.autocomplete-suggestion-item {
  border-radius: 0px;
}
.info-row {
  border-radius: 0px;
}
.empty-copy {
  border-radius: 0px;
}
.profile-note {
  border-radius: 0px;
}
```

- [ ] **Step 5: Verify and Commit**

Run `npm run build` and commit:
```bash
git add src/features/auth/components/OnboardingDialog.vue
git commit -m "style: remove rounded corners on bubbles, buttons, progress bar, and autocomplete"
```

---

### Task 3: Compilation and Verification

- [ ] **Step 1: Run production build**

Run: `npm run build`
Expected: PASS with no compilation/typescript errors.
