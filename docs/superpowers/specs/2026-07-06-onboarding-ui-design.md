# Onboarding Dialog Redesign Spec (Zero-Rounded-Corner Academic Grid)

## Metadata
* **Topic**: Onboarding Dialog Redesign
* **Date**: 2026-07-06
* **Status**: Approved
* **Target File**: [OnboardingDialog.vue](file:///Users/apple/Code/software/src/features/auth/components/OnboardingDialog.vue)

---

## 1. Design Philosophy (Structured Academic Grid)
Since this is an educational/teaching platform, the design will adhere to a **Structured Academic Grid / Swiss Modernism** style. It aims to look clean, highly readable, structured like a textbook/syllabus, and extremely professional.

### Core Visual Guidelines
* **Zero Rounded Corners**: All components (dialog container, step items, message boxes, buttons, autocomplete dropdowns, status rows) must have `border-radius: 0` or `border-radius: 0px`.
* **Crisp Grid Lines**: Use clean `1px` or `2px` solid dark borders (`#0f172a` or `#1e293b`) for structured panels.
* **Readable Typography**: Monospace text for metadata, steps, progress values, and clear sans-serif for content.
* **Accent & Interactive Colors**: Keep existing brand teal/cyan colors (`var(--color-primary)` and `var(--color-action)`) for selections and progress highlights.

---

## 2. Component Layout & Behavior Changes

### 2.1 Dialog Framework (`.onboarding-container`)
* Remove rounded corners: change `border-radius: 26px` to `border-radius: 0`.
* Change border to `2px solid #0f172a`.
* Box shadow: Change to a clean flat offset box shadow `6px 6px 0px 0px rgba(15, 23, 42, 0.15)`.

### 2.2 Left Step Timeline (`.step-rail`)
* Remove rounded corners: `border-radius: 0`.
* Steps list items (`.step-item`): Change to rectangular boxes with `border-radius: 0`.
* Active step: Solid border `2px solid #0f172a`, background `rgba(20, 184, 166, 0.08)`.
* Done step: Slate text, clean light grey background.
* Step index (`.step-index`): Sharp square box with right border.

### 2.3 Chat Dialogue Area (`.chat-card` & Message Bubbles)
* **Message Bubbles (`.message-bubble`)**: Remove rounded corners (`border-radius: 0`).
* **Assistant Message**: 
  * Background: `#ffffff`.
  * Border: `1px solid #0f172a`.
  * Left accent: A thick `3px solid var(--color-primary)` vertical indicator on the left edge.
* **User Message**: 
  * Background: `var(--color-primary)`.
  * Border: `1px solid #0f172a`.
  * Color: `#ffffff`.
  * Shadow: `4px 4px 0px 0px rgba(15, 23, 42, 0.1)`.
* **Selectable Quick Replies (`.quick-reply-btn`)**:
  * Shape: Rectangular (`border-radius: 0`).
  * Default style: `1px solid #0f172a` outline, `#ffffff` background.
  * Selected style: `background: #0f172a`, `color: #ffffff`.
  * Hover style: `background: rgba(20, 184, 166, 0.08)`.
* **Interactive Position**: AI question content and quick replies are outputted as part of the assistant bubble, always aligning directly above the bottom input composer.

### 2.4 Bottom Input Composer (`.composer-wrapper`)
* Change `.composer-wrapper` to have `border-radius: 0`, `border: 2px solid #0f172a`, and clean shadow `4px 4px 0px 0px rgba(15, 23, 42, 0.1)`.
* Send button (`.send-btn`): `border-radius: 0`, `border: 1px solid #0f172a`.

### 2.5 Right Side Progress & Details (`.profile-panel`)
* **Progress Bar (replacing Progress Ring)**:
  * Remove circular SVG / conic gradient ring (`border-radius: 999px`).
  * Style the `.progress-ring` div container as a horizontal progress bar wrapper (`border-radius: 0`, `border: 2px solid #0f172a`, `height: 28px`, `background: #f1f5f9`).
  * Animate progress fill inside using absolute pseudo-element `::after` mapped to `--progress`.
* **Confirmed / Pending Fields (`.info-row`)**:
  * Remove rounded corners: `border-radius: 0`.
  * Confirmed state: `border: 1px solid #0f172a`, light teal background `rgba(20, 184, 166, 0.05)`.
  * Pending state: `border: 1px dashed #94a3b8`.
* **Profile Note (`.profile-note`)**:
  * Remove rounded corners: `border-radius: 0`.
  * Border: `1px solid #0f172a`.
  * Shadow: `3px 3px 0px 0px rgba(15, 23, 42, 0.1)`.

---

## 3. Verification Plan
* Run `npm run build` to verify there are no typescript or compile errors.
* Validate that no rounded corners exist on any dialog components.
* Verify tags selection highlights and selects correctly.
