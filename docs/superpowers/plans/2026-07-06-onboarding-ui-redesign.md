# Onboarding Dialog Redesign Implementation Plan (Glacier Teal System Aligned)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Redesign the first-login onboarding information page to have 100% zero rounded corners (sharp edges) while strictly preserving the system's "Glacier Teal" color palette, theme tokens, and typography.

**Architecture:** Modify the CSS in `OnboardingDialog.vue` to override all `border-radius` styles to 0px, implement a horizontal progress bar instead of a circular progress ring, and style chat elements as sharp academic notecards using the existing Glacier Teal variables.

**Tech Stack:** Vue 3, TypeScript, Tailwind v4, CSS.

---

### Task 1: Zero Rounded Corners on Container, Header, and Step Rail

**Files:**
- Modify: `src/features/auth/components/OnboardingDialog.vue`

- [ ] **Step 1: Replace container dialog styles to remove rounded corners (preserving original colors)**

Replace lines 1229-1246 in CSS:
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

- [ ] **Step 2: Replace skip button, progress badge, and header elements to remove rounded corners (preserving colors)**

Replace lines 1274-1293 and lines 1310-1318 in CSS:
```css
.progress-badge {
  position: absolute;
  top: 32px;
  left: 24px;
  z-index: 4;
  min-width: 96px;
  height: 48px;
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  justify-content: center;
  padding: 7px 12px;
  border: 1px solid rgba(158, 218, 216, 0.78);
  border-radius: 0px; /* zero rounded corners */
  background: rgba(255, 255, 255, 0.78);
  backdrop-filter: blur(14px);
  box-shadow:
      0 12px 28px rgba(15, 23, 42, 0.06),
      0 1px 0 rgba(255, 255, 255, 0.9) inset;
}

.skip-btn {
  position: absolute;
  top: 40px;
  right: 24px;
  z-index: 5;
  height: 32px;
  padding: 0 15px;
  border: 1px solid rgba(158, 218, 216, 0.76);
  border-radius: 0px; /* zero rounded corners */
  background: rgba(255, 255, 255, 0.66);
  color: #41676d;
  font-size: 12px;
  font-weight: 850;
  cursor: pointer;
  backdrop-filter: blur(14px);
  transition:
      transform 0.18s ease,
      border-color 0.18s ease,
      background 0.18s ease,
      color 0.18s ease,
      box-shadow 0.18s ease;
}
```

- [ ] **Step 3: Modify step timeline and rail styles to remove rounded corners**

Replace lines 1393-1404 and steps items styles in CSS:
```css
.step-rail,
.profile-panel {
  min-height: 0;
  overflow: hidden;
  border: 1px solid rgba(183, 226, 224, 0.9);
  border-radius: 0px; /* zero rounded corners */
  background: rgba(255, 255, 255, 0.82);
  box-shadow:
      0 16px 42px rgba(15, 23, 42, 0.06),
      0 1px 0 rgba(255, 255, 255, 0.94) inset;
  backdrop-filter: blur(18px);
}

.step-rail-title {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 6px;
  margin-bottom: 12px;
  padding: 8px 10px;
  border-radius: 0px; /* zero rounded corners */
  background: linear-gradient(135deg, rgba(225, 250, 248, 0.96), rgba(255, 255, 255, 0.96));
  color: var(--color-primary-text);
}

.step-item {
  display: grid;
  grid-template-columns: 28px minmax(0, 1fr);
  gap: 8px;
  align-items: center;
  min-height: 46px;
  padding: 6px 8px;
  border: 1px solid transparent;
  border-radius: 0px; /* zero rounded corners */
  color: #6b7f87;
}

.step-item.active {
  border-color: rgba(20, 160, 157, 0.34);
  background: rgba(231, 250, 248, 0.8);
  color: var(--color-primary-text);
}

.step-item.done {
  color: #315f66;
  background: rgba(248, 253, 252, 0.88);
}

.step-index {
  width: 28px;
  height: 28px;
  display: grid;
  place-items: center;
  border-radius: 0px; /* zero rounded corners */
  color: #78919a;
  background: rgba(236, 248, 247, 0.9);
  font-size: 12px;
  font-weight: 950;
}

.step-item.active .step-index,
.step-item.done .step-index {
  color: #ffffff;
  background: linear-gradient(145deg, var(--color-primary), var(--color-action));
}
```

- [ ] **Step 4: Clean up `.title-mark` visual indicators in header to remove rounded corners**

Replace `.title-mark` styles in CSS:
```css
.title-mark span:first-child {
  width: 32px;
  height: 5px;
  border-radius: 0px; /* zero rounded corners */
  background: linear-gradient(90deg, var(--color-primary), var(--color-action));
  box-shadow: 0 8px 20px rgba(70, 184, 180, 0.2);
}

.title-mark span:last-child {
  width: 6px;
  height: 6px;
  border-radius: 0px; /* zero rounded corners */
  background: #93c5fd;
}
```

- [ ] **Step 5: Verify and Commit**

Run:
```bash
git add src/features/auth/components/OnboardingDialog.vue
git commit -m "style: remove rounded corners on container, badge, and step rail"
```

---

### Task 2: Redesign Chat Card, Message Bubbles, and Quick Reply Tags

**Files:**
- Modify: `src/features/auth/components/OnboardingDialog.vue`

- [ ] **Step 1: Remove rounded corners on `.chat-card` and `.current-question`**

Replace lines 1500-1524 in CSS:
```css
.chat-card {
  position: relative;
  z-index: 1;
  min-height: 0;
  display: grid;
  grid-template-rows: auto minmax(0, 1fr) auto;
  margin: 0;
  overflow: hidden;
  border: 1px solid rgba(183, 226, 224, 0.96);
  border-radius: 0px; /* zero rounded corners */
  background: rgba(255, 255, 255, 0.86);
  box-shadow:
      0 18px 48px rgba(15, 23, 42, 0.08),
      0 1px 0 rgba(255, 255, 255, 0.95) inset;
  backdrop-filter: blur(18px);
}

.current-question {
  display: block;
  padding: 16px 22px;
  border-bottom: 1px solid rgba(203, 235, 233, 0.82);
  background:
      linear-gradient(120deg, rgba(232, 250, 248, 0.92), rgba(255, 255, 255, 0.94) 54%, rgba(240, 253, 250, 0.88)),
      #ffffff;
}
```

- [ ] **Step 2: Update message bubble styles and avatars to be sharp rectangles**

Replace lines 1592-1603 and lines 1638-1657 in CSS:
```css
.avatar-icon,
.user-avatar {
  flex: 0 0 auto;
  width: 38px;
  height: 38px;
  display: grid;
  place-items: center;
  border-radius: 0px; /* zero rounded corners */
  font-size: 13px;
  font-weight: 950;
}

.avatar-icon {
  color: var(--color-primary-text);
  background:
      linear-gradient(145deg, rgba(235, 251, 249, 0.95), rgba(213, 246, 243, 0.95));
  border: 1px solid rgba(158, 218, 216, 0.88);
  box-shadow: 0 12px 24px rgba(70, 184, 180, 0.12);
}

.user-avatar {
  color: #ffffff;
  background: linear-gradient(145deg, var(--color-primary), var(--color-action));
  box-shadow: 0 12px 24px rgba(59, 130, 246, 0.22);
}

.message-bubble {
  position: relative;
  border: 1px solid rgba(203, 235, 233, 0.98);
  border-radius: 0px; /* zero rounded corners */
  background: rgba(255, 255, 255, 0.96);
  box-shadow:
      0 12px 28px rgba(15, 23, 42, 0.06),
      0 1px 0 rgba(255, 255, 255, 0.96) inset;
}

.message-row.assistant .message-bubble {
  border-left: 3px solid var(--color-primary); /* Left accent bar instead of rounded corner */
}

.message-row.user .message-bubble {
  border-color: transparent;
  background: linear-gradient(145deg, var(--color-primary), var(--color-action));
  box-shadow: 0 14px 28px rgba(20, 160, 157, 0.2);
}
```

- [ ] **Step 3: Update quick reply buttons and confirm selection buttons to be sharp blocks**

Replace lines 1721-1736 and lines 1875-1905 in CSS:
```css
.confirm-selection-btn {
  height: 34px;
  padding: 0 13px;
  border: none;
  border-radius: 0px; /* zero rounded corners */
  color: #ffffff;
  background: linear-gradient(145deg, var(--color-primary), var(--color-action));
  font-size: 12px;
  font-weight: 950;
  cursor: pointer;
}

.confirm-selection-btn:disabled {
  cursor: not-allowed;
  opacity: 0.45;
}

.quick-reply-btn {
  height: 32px;
  padding: 0 14px;
  border: 1px solid rgba(20, 184, 166, 0.32);
  border-radius: 0px; /* zero rounded corners */
  background: #ffffff;
  color: #3f6e72;
  font-size: 12px;
  font-weight: 750;
  cursor: pointer;
  transition: all 0.15s ease;
}

.quick-reply-btn:hover {
  border-color: var(--color-primary);
  background: rgba(20, 184, 166, 0.06);
  color: var(--color-primary-text);
  transform: translateY(-1px);
}

.quick-reply-btn.is-selected {
  color: #ffffff;
  border-color: transparent;
  background: linear-gradient(135deg, var(--color-primary), var(--color-action));
  box-shadow: none;
}
```

- [ ] **Step 4: Verify and Commit**

Run:
```bash
git add src/features/auth/components/OnboardingDialog.vue
git commit -m "style: remove rounded corners on chat elements and quick replies"
```

---

### Task 3: Redesign Input Dock, Progress Bar, Details Panel, and Mobile Layout

**Files:**
- Modify: `src/features/auth/components/OnboardingDialog.vue`

- [ ] **Step 1: Replace circular progress ring with a horizontal rectangular progress bar**

Replace lines 2058-2078 in CSS:
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

- [ ] **Step 2: Update Input composer, Send button, and footer wrapper styles to be sharp**

Replace lines 1923-1936 and lines 1958-1984 in CSS:
```css
.composer-wrapper {
  position: relative;
  display: grid;
  grid-template-columns: minmax(0, 1fr) 46px;
  gap: 10px;
  align-items: end;
  padding: 8px;
  border: 1px solid rgba(20, 160, 157, 0.5);
  border-radius: 0px; /* zero rounded corners */
  background: rgba(255, 255, 255, 0.96);
  box-shadow:
      0 0 0 5px rgba(20, 184, 166, 0.08),
      0 16px 34px rgba(15, 23, 42, 0.08);
}

.send-btn {
  width: 46px;
  height: 46px;
  border: none;
  border-radius: 0px; /* zero rounded corners */
  display: grid;
  place-items: center;
  color: #ffffff;
  background: linear-gradient(145deg, var(--color-primary), var(--color-action));
  box-shadow: 0 14px 28px rgba(70, 184, 180, 0.24);
  cursor: pointer;
  transition:
      transform 0.16s ease,
      opacity 0.16s ease,
      box-shadow 0.16s ease;
}

.send-btn:hover:not(:disabled) {
  transform: translateY(-1px);
  box-shadow: 0 18px 34px rgba(70, 184, 180, 0.28);
}
```

- [ ] **Step 3: Update right details panel (`.info-row`), Note box, and mobile layout to remove rounded corners**

Replace `.info-row`, `.profile-note`, and media query classes in CSS:
```css
.info-row {
  display: grid;
  grid-template-columns: 76px minmax(0, 1fr);
  gap: 10px;
  align-items: center;
  min-height: 32px;
  padding: 6px 10px;
  border-radius: 0px; /* zero rounded corners */
  font-size: 12px;
}

.info-row.confirmed {
  border: 1px solid rgba(183, 226, 224, 0.88);
  background: rgba(246, 254, 253, 0.9);
}

.info-row.pending {
  border: 1px dashed rgba(183, 226, 224, 0.9);
  background: rgba(255, 255, 255, 0.58);
}

.empty-copy {
  margin: 0;
  padding: 13px;
  border-radius: 0px; /* zero rounded corners */
  background: rgba(246, 254, 253, 0.86);
  color: #6f8790;
  font-size: 12px;
  font-weight: 800;
}

.profile-note {
  margin-top: auto;
  align-self: stretch;
  padding: 13px;
  border: 1px solid rgba(20, 160, 157, 0.18);
  border-radius: 0px; /* zero rounded corners */
  background: linear-gradient(145deg, #e9fbf9, #ffffff);
  box-shadow: 0 -8px 24px rgba(255, 255, 255, 0.82);
}
```

And in `@media (max-width: 860px)` replace:
```css
  .chat-card {
    border-radius: 0px; /* zero rounded corners */
    min-height: 560px;
  }
```

- [ ] **Step 4: Verify and Commit**

Run:
```bash
git add src/features/auth/components/OnboardingDialog.vue
git commit -m "style: remove rounded corners on composer, progress bar, and info blocks"
```

---

### Task 4: Compilation and Verification

- [ ] **Step 1: Run production build**

Run: `npm run build`
Expected: PASS with no compilation/typescript errors.
