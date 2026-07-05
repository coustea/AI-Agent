# Onboarding Dialog Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Redesign the first-login onboarding information page to adhere to a clean, straight-edge Academic Grid / Swiss Modernism style with 100% zero rounded corners.

**Architecture:** Modify the CSS in `OnboardingDialog.vue` to override all `border-radius` styles to 0px, implement a horizontal progress bar instead of a circular progress ring, and style chat elements as sharp academic notecards.

**Tech Stack:** Vue 3, TypeScript, Tailwind v4, CSS.

---

### Task 1: Zero Rounded Corners on Container, Header, and Step Rail

**Files:**
- Modify: `src/features/auth/components/OnboardingDialog.vue`

- [ ] **Step 1: Replace container dialog styles to remove rounded corners**

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
  border: 2px solid #0f172a;
  border-radius: 0px;
  background: #ffffff;
  box-shadow: 6px 6px 0px 0px rgba(15, 23, 42, 0.15);
}
```

- [ ] **Step 2: Replace skip button, progress badge, and header border styles to remove rounded corners**

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
  border: 2px solid #0f172a;
  border-radius: 0px;
  background: rgba(255, 255, 255, 0.95);
  box-shadow: 3px 3px 0px 0px rgba(15, 23, 42, 0.1);
}

.skip-btn {
  position: absolute;
  top: 40px;
  right: 24px;
  z-index: 5;
  height: 32px;
  padding: 0 15px;
  border: 2px solid #0f172a;
  border-radius: 0px;
  background: #ffffff;
  color: #0f172a;
  font-size: 12px;
  font-weight: 850;
  cursor: pointer;
  transition: all 0.15s ease;
}

.skip-btn:hover {
  background: rgba(15, 23, 42, 0.05);
  transform: translate(1px, 1px);
}
```

- [ ] **Step 3: Modify step timeline and rail styles to remove rounded corners**

Replace lines 1393-1404 and steps items styles in CSS:
```css
.step-rail,
.profile-panel {
  min-height: 0;
  overflow: hidden;
  border: 2px solid #0f172a;
  border-radius: 0px;
  background: #ffffff;
  box-shadow: 4px 4px 0px 0px rgba(15, 23, 42, 0.05);
}

.step-rail-title {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 6px;
  margin-bottom: 12px;
  padding: 8px 10px;
  border-radius: 0px;
  border-bottom: 2px solid #0f172a;
  background: #f8fafc;
  color: #0f172a;
}

.step-item {
  display: grid;
  grid-template-columns: 28px minmax(0, 1fr);
  gap: 8px;
  align-items: center;
  min-height: 46px;
  padding: 6px 8px;
  border: 1px solid #e2e8f0;
  border-radius: 0px;
  color: #64748b;
}

.step-item.active {
  border: 2px solid #0f172a;
  background: rgba(20, 184, 166, 0.08);
  color: #0f172a;
}

.step-item.done {
  color: #0f172a;
  background: #f8fafc;
  border-color: #cbd5e1;
}

.step-index {
  width: 28px;
  height: 28px;
  display: grid;
  place-items: center;
  border-radius: 0px;
  border: 1px solid #0f172a;
  color: #0f172a;
  background: #ffffff;
  font-size: 12px;
  font-weight: 950;
}

.step-item.active .step-index,
.step-item.done .step-index {
  color: #ffffff;
  background: var(--color-primary);
  border-color: var(--color-primary);
}
```

- [ ] **Step 4: Commit changes for Task 1**

Run:
```bash
git add src/features/auth/components/OnboardingDialog.vue
git commit -m "style: remove rounded corners on container, badge, and step rail"
```

---

### Task 2: Redesign Chat Card, Message Bubbles, and Quick Reply Tags

**Files:**
- Modify: `src/features/auth/components/OnboardingDialog.vue`

- [ ] **Step 1: Remove rounded corners and apply flat shadow on `.chat-card` and `.current-question`**

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
  border: 2px solid #0f172a;
  border-radius: 0px;
  background: #ffffff;
  box-shadow: 4px 4px 0px 0px rgba(15, 23, 42, 0.08);
}

.current-question {
  display: block;
  padding: 16px 22px;
  border-bottom: 2px solid #0f172a;
  background: #f8fafc;
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
  border-radius: 0px;
  border: 2px solid #0f172a;
  font-size: 13px;
  font-weight: 950;
}

.avatar-icon {
  color: #0f172a;
  background: #ffffff;
  box-shadow: 2px 2px 0px 0px #0f172a;
}

.user-avatar {
  color: #ffffff;
  background: #0f172a;
  box-shadow: 2px 2px 0px 0px var(--color-primary);
}

.message-bubble {
  position: relative;
  border: 1px solid #0f172a;
  border-radius: 0px;
  background: #ffffff;
  box-shadow: 3px 3px 0px 0px rgba(15, 23, 42, 0.05);
}

.message-row.assistant .message-bubble {
  border-left: 3px solid var(--color-primary);
}

.message-row.user .message-bubble {
  border: 1px solid #0f172a;
  background: var(--color-primary);
  box-shadow: 3px 3px 0px 0px rgba(15, 23, 42, 0.1);
}
```

- [ ] **Step 3: Update quick reply buttons and confirm selection buttons to be sharp blocks**

Replace lines 1721-1736 and lines 1875-1905 in CSS:
```css
.confirm-selection-btn {
  height: 34px;
  padding: 0 13px;
  border: 1px solid #0f172a;
  border-radius: 0px;
  color: #ffffff;
  background: #0f172a;
  font-size: 12px;
  font-weight: 950;
  cursor: pointer;
  box-shadow: 2px 2px 0px 0px rgba(15, 23, 42, 0.15);
}

.confirm-selection-btn:disabled {
  cursor: not-allowed;
  opacity: 0.45;
  box-shadow: none;
}

.quick-reply-btn {
  height: 32px;
  padding: 0 14px;
  border: 1px solid #0f172a;
  border-radius: 0px;
  background: #ffffff;
  color: #0f172a;
  font-size: 12px;
  font-weight: 750;
  cursor: pointer;
  transition: all 0.15s ease;
}

.quick-reply-btn:hover {
  background: rgba(20, 184, 166, 0.08);
  transform: translate(1px, 1px);
}

.quick-reply-btn.is-selected {
  color: #ffffff;
  background: var(--color-primary);
  border-color: var(--color-primary);
  box-shadow: none;
}
```

- [ ] **Step 4: Commit changes for Task 2**

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
  border: 2px solid #0f172a;
  background: #f1f5f9;
  border-radius: 0px;
  overflow: hidden;
  box-shadow: 3px 3px 0px 0px rgba(15, 23, 42, 0.1);
}

.progress-ring::after {
  content: '';
  position: absolute;
  left: 0;
  top: 0;
  bottom: 0;
  width: calc(var(--progress) * 1%);
  background: var(--color-primary);
  transition: width 0.3s ease;
}

.progress-ring span {
  position: relative;
  z-index: 2;
  color: #0f172a;
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
  border: 2px solid #0f172a;
  border-radius: 0px;
  background: #ffffff;
  box-shadow: 4px 4px 0px 0px rgba(15, 23, 42, 0.1);
}

.send-btn {
  width: 46px;
  height: 46px;
  border: 1px solid #0f172a;
  border-radius: 0px;
  display: grid;
  place-items: center;
  color: #ffffff;
  background: #0f172a;
  box-shadow: 2px 2px 0px 0px rgba(15, 23, 42, 0.2);
  cursor: pointer;
  transition: all 0.16s ease;
}

.send-btn:hover:not(:disabled) {
  transform: translate(1px, 1px);
  box-shadow: 1px 1px 0px 0px rgba(15, 23, 42, 0.2);
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
  border-radius: 0px;
  font-size: 12px;
}

.info-row.confirmed {
  border: 1px solid #0f172a;
  background: rgba(20, 184, 166, 0.05);
}

.info-row.pending {
  border: 1px dashed #cbd5e1;
  background: transparent;
}

.empty-copy {
  margin: 0;
  padding: 13px;
  border-radius: 0px;
  border: 1px dashed #cbd5e1;
  background: #f8fafc;
  color: #64748b;
  font-size: 12px;
  font-weight: 800;
}

.profile-note {
  margin-top: auto;
  align-self: stretch;
  padding: 13px;
  border: 2px solid #0f172a;
  border-radius: 0px;
  background: #ffffff;
  box-shadow: 3px 3px 0px 0px rgba(15, 23, 42, 0.05);
}
```

And in `@media (max-width: 860px)` replace:
```css
  .chat-card {
    border-radius: 0px;
    min-height: 560px;
  }
```

- [ ] **Step 4: Commit changes for Task 3**

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
