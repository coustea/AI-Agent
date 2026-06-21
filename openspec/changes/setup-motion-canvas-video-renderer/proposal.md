## Why

The AI Learning Platform currently has a backend-driven video schema generation pipeline (`videoAgent`) but lacks a corresponding animation rendering engine to produce the actual video files or storyboards. To turn structural video plans (`TeachingVideoPlan` JSON payloads) into clear, high-quality, and exportable computer science teaching animations, we need a dedicated frontend video rendering service. Motion Canvas provides a programmatic, timeline-based animation framework in TypeScript that perfectly maps to structural JSON structures, making it the ideal candidate for rendering deterministic, reproducible teaching animations.

## What Changes

- Create a new, standalone `video-render-service` directory at the repository root.
- Implement the Motion Canvas configuration using `@motion-canvas/2d`, `@motion-canvas/core`, and `@motion-canvas/ffmpeg`.
- Establish a strict schema validation layer for `TeachingVideoPlan` and a modular `TemplateRegistry` inside the render service.
- Implement 12 core computer science teaching scene templates (covering data structures, OS scheduling, network sequence protocols, and programming language execution).
- Implement reusable visual blocks (FrameLayout, light-theme CodeBlock, QueueBox, MetricTable, TimelineBar, NodeBox, Arrow).
- Integrate RenderMode controls (`quick` for 720p draft rendering, `standard` for 1080p standard, `detailed` for complex rendering) to manage animation rendering budgets.
- Add support for generating MP4 videos using the `@motion-canvas/ffmpeg` exporter.

## Capabilities

### New Capabilities
- `video-render-service`: Programmatic Motion Canvas rendering engine for computer science educational videos matching the backend `TeachingVideoPlan` schema contracts.

### Modified Capabilities
<!-- No modified capabilities; this is a brand new standalone service -->

## Impact

- **New Folder**: `/video-render-service` containing the standalone Node/TS project.
- **Backend VideoAgent Integration**: Backend `VideoAgent` outputs can be piped directly into `video-render-service` to output MP4 educational videos.
- **Dependencies**: Adds Motion Canvas dependencies (`@motion-canvas/core`, `@motion-canvas/2d`, `@motion-canvas/ffmpeg`) and typescript compiler devDependencies.
