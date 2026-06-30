export type SceneType =
  | "title_intro"
  | "concept_explain"
  | "process_flow"
  | "state_machine"
  | "data_structure"
  | "algorithm_trace"
  | "memory_layout"
  | "cpu_architecture"
  | "network_protocol"
  | "layered_architecture"
  | "code_execution"
  | "compare_summary"
  | "knowledge_check"
  // CS Theory templates
  | "array_linked_list"
  | "stack_queue"
  | "process_state"
  | "storage_hierarchy";

export interface SubtitleChunk {
  start: number;
  end: number;
  text: string;
}

export interface CaptionWord {
  text: string;
  start_ms: number;
  end_ms: number;
}

export interface CaptionChunk {
  text: string;
  start_ms: number;
  end_ms: number;
}

export type VisualCueKind =
  | "define"
  | "example"
  | "trace_step"
  | "compare"
  | "misconception"
  | "checkpoint"
  | "recap";

export interface VisualCue {
  id: string;
  kind: VisualCueKind;
  target: string;
  summary: string;
  start_ms: number;
  end_ms: number;
  caption_text?: string | null;
}

export interface RichVideoScene {
  id: string;
  type: SceneType;
  duration_ms: number;
  duration_seconds: number;
  audio_duration_ms: number;
  title: string;
  narration: string;
  visual: Record<string, unknown>;
  audio_src?: string;
  transition: "fade" | "slide_left" | "slide_up" | "zoom" | "none";
  caption_words?: CaptionWord[];
  caption_chunks?: CaptionChunk[];
  visual_cues?: VisualCue[];
}

export interface VideoMeta {
  video_id: string;
  title: string;
  subject: string;
  topic: string;
  difficulty: "入门" | "基础" | "中等" | "进阶" | string;
  target_audience: string;
  estimated_duration_seconds: number;
  language: "zh-CN" | string;
}

export interface GlobalStyle {
  theme:
    | "clean_tech_education"
    | "blueprint_academic"
    | "soft_future_classroom";
  background:
    | "soft_grid_gradient"
    | "circuit_board_light"
    | "minimal_blueprint";
  primary_color: string;
  accent_color: string;
  danger_color: string;
  success_color: string;
  font_family: string;
  visual_density?: "medium" | "rich";
  layout_style?: "card_plus_diagram" | "lab_dashboard" | "timeline_explainer";
  motion_style?: "smooth_explanatory" | "step_by_step" | "focus_zoom";
}

export interface RenderConfig {
  width: number;
  height: number;
  fps: number;
  format: "mp4" | string;
  default_scene_transition:
    | "fade"
    | "slide_left"
    | "slide_up"
    | "zoom"
    | "none";
  subtitle_enabled: boolean;
  voiceover_enabled: boolean;
}

export interface BgmConfig {
  bgm_src?: string;
  bgm_volume: number;
}

export interface RichVideoPlan {
  meta: VideoMeta;
  global_style: GlobalStyle;
  render_config: RenderConfig;
  audio?: BgmConfig;
  scenes: RichVideoScene[];
}
export type SceneTransitionType =
  | "fade"
  | "slide_left"
  | "slide_up"
  | "zoom"
  | "none";
