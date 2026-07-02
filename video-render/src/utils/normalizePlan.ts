import {
  RichVideoPlan,
  RichVideoScene,
  GlobalStyle,
  RenderConfig,
  VideoMeta,
  SceneType,
} from "../schema/types";

// Default Styles and Configurations
const DEFAULT_GLOBAL_STYLE: GlobalStyle = {
  theme: "clean_tech_education",
  background: "soft_grid_gradient",
  primary_color: "#2563eb",
  accent_color: "#3b82f6",
  danger_color: "#ef4444",
  success_color: "#10b981",
  font_family: "Inter, system-ui, sans-serif",
};

const DEFAULT_RENDER_CONFIG: RenderConfig = {
  width: 1920,
  height: 1080,
  fps: 30,
  format: "mp4",
  default_scene_transition: "fade",
  subtitle_enabled: true,
  voiceover_enabled: false,
};

// Valid Union Lists for runtime validation/fallback mapping
const VALID_THEMES = [
  "clean_tech_education",
  "blueprint_academic",
  "soft_future_classroom",
];
const VALID_BACKGROUNDS = [
  "soft_grid_gradient",
  "circuit_board_light",
  "minimal_blueprint",
];
const VALID_TRANSITIONS = ["fade", "slide_left", "slide_up", "zoom", "none"];
const VALID_SCENE_TYPES: SceneType[] = [
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
  // CS Theory templates
  "array_linked_list",
  "stack_queue",
  "process_state",
  "storage_hierarchy",
];

/**
 * Determines the SceneType based on available information.
 * Priority: explicit type > visual_type > default
 */
function determineSceneType(
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  scene: any,
  idx: number,
  isLastScene: boolean,
): SceneType {
  // 1. Use explicit type if valid
  if (scene.type && VALID_SCENE_TYPES.includes(scene.type)) {
    return scene.type;
  }

  // 2. Use visual_type if valid
  if (scene.visual_type && VALID_SCENE_TYPES.includes(scene.visual_type)) {
    return scene.visual_type as SceneType;
  }

  // 3. Default based on position
  if (idx === 0) {
    return "title_intro";
  }
  if (isLastScene) {
    return "compare_summary";
  }
  return "concept_explain";
}

/**
 * Normalizes input JSON into the schema format expected by the frontend.
 * Supports both rich_video_plan.json (V2) and backend VideoPayload formats.
 */
// eslint-disable-next-line @typescript-eslint/no-explicit-any
export function normalizePlan(rawPlan: any): RichVideoPlan {
  if (!rawPlan) {
    throw new Error("Input video plan is null or undefined");
  }

  const meta: VideoMeta = {
    video_id: rawPlan.meta?.video_id || rawPlan.video_id || "generated_video",
    title: rawPlan.meta?.title || rawPlan.title || "讲解视频",
    subject: rawPlan.meta?.subject || rawPlan.topic || "计算机理论",
    topic: rawPlan.meta?.topic || rawPlan.topic || "主题讲解",
    difficulty: rawPlan.meta?.difficulty || "基础",
    target_audience: rawPlan.meta?.target_audience || "学生",
    estimated_duration_seconds:
      rawPlan.meta?.estimated_duration_seconds ||
      rawPlan.duration_seconds ||
      60,
    language: rawPlan.meta?.language || rawPlan.language || "zh-CN",
  };

  // Safe mapping of global style
  const rawStyle = rawPlan.global_style || {};
  const theme = VALID_THEMES.includes(rawStyle.theme)
    ? rawStyle.theme
    : DEFAULT_GLOBAL_STYLE.theme;
  const background = VALID_BACKGROUNDS.includes(rawStyle.background)
    ? rawStyle.background
    : DEFAULT_GLOBAL_STYLE.background;

  const globalStyle: GlobalStyle = {
    theme,
    background,
    primary_color: rawStyle.primary_color || DEFAULT_GLOBAL_STYLE.primary_color,
    accent_color: rawStyle.accent_color || DEFAULT_GLOBAL_STYLE.accent_color,
    danger_color: rawStyle.danger_color || DEFAULT_GLOBAL_STYLE.danger_color,
    success_color: rawStyle.success_color || DEFAULT_GLOBAL_STYLE.success_color,
    font_family: rawStyle.font_family || DEFAULT_GLOBAL_STYLE.font_family,
  };

  // Safe mapping of render config
  const rawConfig = rawPlan.render_config || {};
  const default_scene_transition = VALID_TRANSITIONS.includes(
    rawConfig.default_scene_transition,
  )
    ? rawConfig.default_scene_transition
    : DEFAULT_RENDER_CONFIG.default_scene_transition;

  const renderConfig: RenderConfig = {
    width: rawConfig.width || DEFAULT_RENDER_CONFIG.width,
    height: rawConfig.height || DEFAULT_RENDER_CONFIG.height,
    fps: rawConfig.fps || DEFAULT_RENDER_CONFIG.fps,
    format: rawConfig.format || DEFAULT_RENDER_CONFIG.format,
    default_scene_transition,
    subtitle_enabled:
      rawConfig.subtitle_enabled ?? DEFAULT_RENDER_CONFIG.subtitle_enabled,
    voiceover_enabled:
      rawConfig.voiceover_enabled ?? DEFAULT_RENDER_CONFIG.voiceover_enabled,
  };

  const audio = rawPlan.audio || {
    bgm_src: rawPlan.audio?.bgm_src || undefined,
    bgm_volume: rawPlan.audio?.bgm_volume ?? 0.15,
  };

  const rawScenes = rawPlan.scenes || [];
  const scenes: RichVideoScene[] = rawScenes.map(
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    (scene: any, idx: number): RichVideoScene => {
      const id = scene.id || scene.scene_id || `scene_${idx + 1}`;
      const title = scene.title || `分镜 ${idx + 1}`;
      const narration = scene.narration || "";
      const audio_src = scene.audio_src || undefined;

      // Parse scene transition
      const transition = VALID_TRANSITIONS.includes(scene.transition)
        ? scene.transition
        : default_scene_transition;

      // Calculate duration in seconds
      const duration_ms =
        typeof scene.duration_ms === "number"
          ? scene.duration_ms
          : typeof scene.duration_seconds === "number"
            ? Math.round(scene.duration_seconds * 1000)
            : typeof scene.duration === "number"
              ? scene.duration
              : 8000;
      const duration_seconds = duration_ms / 1000;
      const audio_duration_ms =
        typeof scene.audio_duration_ms === "number"
          ? scene.audio_duration_ms
          : Math.max(0, duration_ms);

      // Determine scene type using the new unified logic
      const isLastScene = idx === rawScenes.length - 1;
      const type = determineSceneType(scene, idx, isLastScene);

      // Use visual data from backend directly
      const visual = scene.visual || {};

      // Pass TTS word-level captions from backend
      const caption_words: Array<{
        text: string;
        start_ms: number;
        end_ms: number;
      }> = Array.isArray(scene.caption_words) ? scene.caption_words : [];
      const caption_chunks = Array.isArray(scene.caption_chunks)
        ? scene.caption_chunks
        : [];
      const visual_cues = Array.isArray(scene.visual_cues)
        ? scene.visual_cues
        : [];

      return {
        id,
        type,
        duration_ms,
        duration_seconds,
        audio_duration_ms,
        title,
        narration,
        visual,
        audio_src,
        // eslint-disable-next-line @remotion/non-pure-animation
        transition: transition as
          | "fade"
          | "slide_left"
          | "slide_up"
          | "zoom"
          | "none",
        caption_words,
        caption_chunks,
        visual_cues,
      };
    },
  );

  return {
    meta,
    global_style: globalStyle,
    render_config: renderConfig,
    audio,
    scenes,
  };
}
