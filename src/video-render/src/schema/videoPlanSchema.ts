import { z } from 'zod';

// Scene Type Enum Schema
export const sceneTypeSchema = z.enum([
  'title_intro',
  'concept_explain',
  'process_flow',
  'state_machine',
  'data_structure',
  'algorithm_trace',
  'memory_layout',
  'cpu_architecture',
  'network_protocol',
  'layered_architecture',
  'code_execution',
  'compare_summary',
  'knowledge_check',
]);

// Rich Video Scene Schema
export const richVideoSceneSchema = z.object({
  id: z.string().optional(),
  scene_id: z.string().optional(),
  type: z.string().optional(),
  visual_type: z.string().optional(),
  duration_seconds: z.number().optional(),
  duration_ms: z.number().optional(),
  title: z.string().optional(),
  narration: z.string().optional(),
  visual: z.record(z.string(), z.unknown()).optional(),
  audio_src: z.string().optional(),
  transition: z.string().optional(),
}).catchall(z.any());

// Video Meta Schema
export const videoMetaSchema = z.object({
  video_id: z.string().optional(),
  title: z.string().optional(),
  subject: z.string().optional(),
  topic: z.string().optional(),
  difficulty: z.string().optional(),
  target_audience: z.string().optional(),
  estimated_duration_seconds: z.number().optional(),
  language: z.string().optional(),
}).catchall(z.any());

// Global Style Schema
export const globalStyleSchema = z.object({
  theme: z.string().optional(),
  background: z.string().optional(),
  primary_color: z.string().optional(),
  accent_color: z.string().optional(),
  danger_color: z.string().optional(),
  success_color: z.string().optional(),
  font_family: z.string().optional(),
  visual_density: z.string().optional(),
  layout_style: z.string().optional(),
  motion_style: z.string().optional(),
}).catchall(z.any());

// Render Config Schema
export const renderConfigSchema = z.object({
  width: z.number().optional(),
  height: z.number().optional(),
  fps: z.number().optional(),
  format: z.string().optional(),
  default_scene_transition: z.string().optional(),
  subtitle_enabled: z.boolean().optional(),
  voiceover_enabled: z.boolean().optional(),
}).catchall(z.any());

// BGM Config Schema
export const bgmConfigSchema = z.object({
  bgm_src: z.string().optional(),
  bgm_volume: z.number().optional(),
}).catchall(z.any());

// Rich Video Plan Schema (Root)
export const richVideoPlanSchema = z.object({
  meta: videoMetaSchema.optional(),
  global_style: globalStyleSchema.optional(),
  render_config: renderConfigSchema.optional(),
  audio: bgmConfigSchema.optional(),
  scenes: z.array(richVideoSceneSchema),
}).catchall(z.any());
