# Motion Canvas Video Rendering Service

This is a standalone video rendering service built on **Motion Canvas**, designed to programmatically generate computer science teaching and explanation videos from structured `TeachingVideoPlan` JSON payloads.

## Tech Stack
- **Framework**: [Motion Canvas](https://motioncanvas.github.io/) (TypeScript, Canvas API, Vite)
- **Exporting**: `@motion-canvas/ffmpeg` (runs FFmpeg locally/headlessly to compile MP4 videos)
- **Theme**: Unified Light Theme (`#F8FAFC` background, `#F1F5F9` code blocks)

---

## Directory Structure
- `src/schema/`: TypeScript typings (`videoPlan.ts`) and validation registry (`templateRegistry.ts`).
- `src/components/`: Reusable, light-themed visual building blocks (`CodeBlock`, `NodeBox`, `Arrow`, `QueueBox`, `TimelineBar`, `MetricTable`, `Badge`).
- `src/renderer/`: Core routing logic (`TemplateRouter.tsx`), mode-based timings (`sceneTiming.ts`), and fallbacks (`ErrorScene.tsx`).
- `src/templates/`: 13 specialized computer science scene templates (recursive functions, trees/graphs traversal, CPU scheduling Gantt charts, process states, sequence lines).
- `src/data/`: Dynamic input plans (`video_plan.json` is the active payload; `video_plan.example.json` is a BFS sample).

---

## Setup & Running

### 1. Install Dependencies
Make sure you have Node.js 18+ and FFmpeg installed on your machine.
Then, install package dependencies:
```bash
npm install
```

### 2. Start the Interactive Editor (Preview)
Start the Vite development server to view, debug, and preview animations interactively in your browser:
```bash
npm run dev
# or: npm start
```
Open the local server URL (default: `http://localhost:5173`) in Chrome or Safari.

### 3. Render and Export Video to MP4
To headlessly render the active `video_plan.json` into an exportable MP4 file:
```bash
npm run render
```
The compiled output will be exported to the `output/` directory as defined in the Motion Canvas configuration.

---

## Render Modes
The rendering duration and detail level adapt automatically to the `video_config.mode` parameter in the JSON plan:
- **`quick`**: Optimized for rapid draft rendering. Caps maximum visible elements (e.g. queue items, table rows) to 5, scales animation transitions down, and renders at 720p.
- **`standard`**: Standard 1080p rendering with full transitions and balanced item limits (up to 10).
- **`detailed`**: High-detail rendering. Allows up to 18 elements on screen with longer, smoother pause intervals.

---

## Backend Orchestration
The backend `videoAgent` compiles materials, outlines, and scene sequences into a `TeachingVideoPlan` matching the schema. The generated JSON is saved to `video-render/src/data/video_plan.json` before triggering the headless renderer.
```
Backend (FastAPI) ───[Writes JSON]───► src/data/video_plan.json ───► npm run render ───► Output MP4
```
