# Frontend Slides HTML Contract

Generate one complete HTML document. All presentation CSS and JavaScript must be
inline. The only permitted network resources are Google Fonts or Fontshare
stylesheets; external scripts are forbidden.

## Fixed Stage

- Include the supplied viewport CSS in full.
- Use one `.deck-viewport` containing one `.deck-stage`.
- Author the stage and every `.slide` at exactly 1920x1080.
- Scale the whole stage uniformly with JavaScript. Letterbox or pillarbox on
  narrow screens; never reflow slide content.
- Switch slides with `.active` and `.visible` through visibility, opacity, and
  pointer events. Never use display switching.

## Content

- Every page is a semantic `<section class="slide">`.
- The first page has `slide active visible`; all later pages start inactive.
- A speaker-led deck uses one central idea, large type, generous space, and no
  more than three short points per page.
- A reading-first deck may use structured grids, tables, annotations, and up to
  eight concise points when comfortably readable.
- Split content into another slide instead of shrinking or overflowing.
- Do not create generic card walls, purple-on-white gradients, or decorative
  elements unrelated to the subject.

## SlidePresentation

Provide a `SlidePresentation` controller that:

- calculates `min(innerWidth / 1920, innerHeight / 1080)`;
- handles Arrow keys, Space, PageUp, PageDown, mouse wheel, and touch swipe;
- exposes `window.presentation`;
- keeps a page count or progress indicator outside the stage.

## Inline Editing

Inline Editing is included by default:

- top-left hover hotzone with a 400ms grace period;
- `E` toggles edit mode unless focus is already in editable text;
- visible slide text becomes `contenteditable`;
- Ctrl/Cmd+S serializes the current document and downloads an HTML Blob;
- do not call a server write endpoint and do not require localStorage.

## Quality And Accessibility

- Use Google Fonts or Fontshare. Do not use Inter, Roboto, Arial, or a system
  font as the display face.
- Include semantic landmarks, useful ARIA labels, and keyboard navigation.
- Include `prefers-reduced-motion`.
- Use clear `/* === SECTION NAME === */` comments throughout CSS and JavaScript.
- No slide may scroll, overflow, overlap, render blank, or use unreadably small
  text.
