import {z} from "zod";

export const sceneTypeSchema = z.enum([
  "title_intro",
  "concept_explain",
  "process_flow",
  "state_machine",
  "data_structure",
  "algorithm_trace",
  "memory_layout",
  "cpu_architecture",
  "network_protocol",
  "layered_architecture",
  "code_execution",
  "compare_summary",
  "knowledge_check",
  "array_linked_list",
  "stack_queue",
  "process_state",
  "storage_hierarchy",
]);

const timedTextSchema = z.object({
  text: z.string().min(1),
  start_ms: z.number().int().nonnegative(),
  end_ms: z.number().int().positive(),
}).strict();

const visualCueSchema = z.object({
  id: z.string().min(1),
  kind: z.enum([
    "define",
    "example",
    "trace_step",
    "compare",
    "misconception",
    "checkpoint",
    "recap",
  ]),
  target: z.string(),
  summary: z.string(),
  start_ms: z.number().int().nonnegative(),
  end_ms: z.number().int().positive(),
  caption_text: z.string().nullable().optional(),
}).strict();

export const videoSceneSchema = z.object({
  scene_id: z.string().min(1),
  index: z.number().int().positive(),
  role: z.enum([
    "hook",
    "concept",
    "example",
    "process",
    "misconception",
    "practice",
    "recap",
  ]),
  title: z.string().min(1),
  learning_objective: z.string().min(1),
  visual_type: sceneTypeSchema,
  visual: z.record(z.string(), z.unknown()),
  narration: z.string().min(1),
  audio_src: z.string().min(1),
  start_ms: z.number().int().nonnegative(),
  duration_ms: z.number().int().positive(),
  audio_duration_ms: z.number().int().positive(),
  caption_words: z.array(timedTextSchema),
  captions: z.array(timedTextSchema),
  visual_cues: z.array(visualCueSchema),
}).strict();

export const videoPlanSchema = z.object({
  schema_version: z.literal("video/v2"),
  title: z.string().min(1),
  topic: z.string().min(1),
  language: z.string().min(1),
  aspect_ratio: z.enum(["16:9", "9:16", "1:1"]),
  style: z.object({
    id: z.enum([
      "precision_light",
      "systems_dark",
      "editorial_classroom",
    ]),
    rationale: z.string().min(1),
  }).strict(),
  render: z.object({
    width: z.number().int().positive(),
    height: z.number().int().positive(),
    fps: z.number().int().min(24).max(60),
    video_codec: z.literal("h264"),
    audio_codec: z.literal("aac"),
    format: z.literal("mp4"),
  }).strict(),
  scenes: z.array(videoSceneSchema).min(1),
  metadata: z.record(z.string(), z.unknown()),
}).strict();

export type VideoPlanV2 = z.infer<typeof videoPlanSchema>;
