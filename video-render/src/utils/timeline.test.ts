import assert from "node:assert/strict";
import test from "node:test";
import type { CaptionChunk, VisualCue } from "../schema/types";
import {
  buildSceneFrameRanges,
  getActiveVisualCue,
  getActiveCaptionChunk,
  getCueDrivenIndex,
  getCueProgress,
} from "./timeline";
import { normalizePlan } from "./normalizePlan";

test("scene frame ranges share rounded boundaries without cumulative drift", () => {
  const ranges = buildSceneFrameRanges([1017, 1017, 1017], 30);

  assert.deepEqual(ranges, [
    { from: 0, durationInFrames: 31 },
    { from: 31, durationInFrames: 30 },
    { from: 61, durationInFrames: 31 },
  ]);
  const lastRange = ranges[ranges.length - 1];
  assert.equal(
    lastRange.from + lastRange.durationInFrames,
    Math.round((3051 / 1000) * 30),
  );
});

test("caption chunks disappear after the spoken audio ends", () => {
  const chunks: CaptionChunk[] = [
    { text: "进程是程序的一次执行过程", start_ms: 0, end_ms: 1800 },
  ];

  assert.equal(getActiveCaptionChunk(chunks, 1200)?.text, chunks[0].text);
  assert.equal(getActiveCaptionChunk(chunks, 1800), undefined);
  assert.equal(getActiveCaptionChunk(chunks, 2200), undefined);
});

test("visual cues choose teaching steps by narration timing", () => {
  const cues: VisualCue[] = [
    {
      id: "beat-1",
      kind: "trace_step",
      target: "steps.0",
      summary: "检查中点",
      start_ms: 300,
      end_ms: 1200,
    },
    {
      id: "beat-2",
      kind: "trace_step",
      target: "steps.1",
      summary: "缩小区间",
      start_ms: 1500,
      end_ms: 2600,
    },
  ];

  assert.equal(getCueDrivenIndex(cues, 200, 2, 3000, ["trace_step"]), 0);
  assert.equal(getCueDrivenIndex(cues, 900, 2, 3000, ["trace_step"]), 0);
  assert.equal(getCueDrivenIndex(cues, 1800, 2, 3000, ["trace_step"]), 1);
  assert.equal(getCueDrivenIndex(cues, 2800, 2, 3000, ["trace_step"]), 1);
});

test("visual cue fallback uses audio duration instead of padded scene duration", () => {
  assert.equal(getCueDrivenIndex([], 1499, 3, 3000, ["trace_step"]), 1);
  assert.equal(getCueDrivenIndex([], 2999, 3, 3000, ["trace_step"]), 2);
  assert.equal(getCueDrivenIndex([], 3400, 3, 3000, ["trace_step"]), 2);
});

test("cue progress follows the active narration interval", () => {
  const cues: VisualCue[] = [
    {
      id: "beat-1",
      kind: "trace_step",
      target: "steps.0",
      summary: "",
      start_ms: 500,
      end_ms: 1500,
    },
  ];

  assert.equal(getCueProgress(cues, 250, 3000, ["trace_step"]), 0);
  assert.equal(getCueProgress(cues, 1000, 3000, ["trace_step"]), 0.5);
  assert.equal(getCueProgress(cues, 1800, 3000, ["trace_step"]), 1);
});

test("active visual cue remains visible through a short narration gap", () => {
  const cues: VisualCue[] = [
    {
      id: "beat-1",
      kind: "define",
      target: "main_concept",
      summary: "先理解定义",
      start_ms: 0,
      end_ms: 900,
    },
    {
      id: "beat-2",
      kind: "example",
      target: "example",
      summary: "再看例子",
      start_ms: 1200,
      end_ms: 2200,
    },
  ];

  assert.equal(getActiveVisualCue(cues, 100)?.id, "beat-1");
  assert.equal(getActiveVisualCue(cues, 1050)?.id, "beat-1");
  assert.equal(getActiveVisualCue(cues, 1500)?.id, "beat-2");
  assert.equal(getActiveVisualCue(cues, 2500), undefined);
});

test("normalization preserves backend narration timing fields", () => {
  const plan = normalizePlan({
    title: "进程",
    topic: "操作系统",
    scenes: [
      {
        scene_id: "scene-1",
        visual_type: "concept_explain",
        duration_ms: 3400,
        audio_duration_ms: 3000,
        title: "进程是什么",
        narration: "进程是程序的一次执行过程。",
        visual: { main_concept: "进程" },
        caption_words: [
          { text: "进程", start_ms: 0, end_ms: 400 },
        ],
        caption_chunks: [
          { text: "进程是程序的一次执行过程。", start_ms: 0, end_ms: 3000 },
        ],
        visual_cues: [
          {
            id: "beat-1",
            kind: "define",
            target: "main_concept",
            summary: "给出定义",
            start_ms: 0,
            end_ms: 3000,
          },
        ],
      },
    ],
  });

  assert.equal(plan.scenes[0].duration_ms, 3400);
  assert.equal(plan.scenes[0].audio_duration_ms, 3000);
  assert.equal(plan.scenes[0].caption_chunks?.length, 1);
  assert.equal(plan.scenes[0].visual_cues?.[0].kind, "define");
});
