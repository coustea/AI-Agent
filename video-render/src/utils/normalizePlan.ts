import type {GlobalStyle, RichVideoPlan, VideoStyleId} from "../schema/types";
import {videoPlanSchema} from "../schema/videoPlanSchema";

const STYLE_TOKENS: Record<VideoStyleId, GlobalStyle> = {
  precision_light: {
    theme: "precision_light",
    background: "technical_grid",
    primary_color: "#155eef",
    accent_color: "#00a878",
    danger_color: "#d92d20",
    success_color: "#039855",
    font_family: '"Inter", "PingFang SC", "Microsoft YaHei", sans-serif',
  },
  systems_dark: {
    theme: "systems_dark",
    background: "system_console",
    primary_color: "#52d3ff",
    accent_color: "#a3e635",
    danger_color: "#fb7185",
    success_color: "#34d399",
    font_family: '"Inter", "PingFang SC", "Microsoft YaHei", sans-serif',
  },
  editorial_classroom: {
    theme: "editorial_classroom",
    background: "editorial_board",
    primary_color: "#14532d",
    accent_color: "#e5484d",
    danger_color: "#b42318",
    success_color: "#15803d",
    font_family: '"Outfit", "PingFang SC", "Microsoft YaHei", sans-serif',
  },
};

export function normalizePlan(rawPlan: unknown): RichVideoPlan {
  const plan = videoPlanSchema.parse(rawPlan);
  const durationMs = plan.scenes.reduce(
    (total, scene) => total + scene.duration_ms,
    0,
  );

  return {
    meta: {
      video_id: String(plan.metadata.video_id ?? "generated_video"),
      title: plan.title,
      subject: "计算机理论",
      topic: plan.topic,
      difficulty: String(plan.metadata.difficulty ?? "基础"),
      target_audience: String(plan.metadata.audience ?? "学习者"),
      estimated_duration_seconds: durationMs / 1000,
      language: plan.language,
    },
    global_style: STYLE_TOKENS[plan.style.id],
    render_config: {
      width: plan.render.width,
      height: plan.render.height,
      fps: plan.render.fps,
      format: "mp4",
      default_scene_transition: "fade",
      subtitle_enabled: true,
      voiceover_enabled: true,
    },
    scenes: plan.scenes.map((scene) => ({
      id: scene.scene_id,
      type: scene.visual_type,
      duration_ms: scene.duration_ms,
      duration_seconds: scene.duration_ms / 1000,
      audio_duration_ms: scene.audio_duration_ms,
      title: scene.title,
      narration: scene.narration,
      visual: scene.visual,
      audio_src: scene.audio_src,
      transition: scene.role === "hook" ? "zoom" : "fade",
      caption_words: scene.caption_words,
      caption_chunks: scene.captions,
      visual_cues: scene.visual_cues,
    })),
  };
}
