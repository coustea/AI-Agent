import type { GlobalStyle, RichVideoPlan, VideoStyleId } from "../schema/types";
import { videoPlanSchema } from "../schema/videoPlanSchema";

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

/**
 * Normalize a flat string array into structured objects with id/label/description.
 * LLMs sometimes generate `["step1", "step2"]` when the component expects
 * `[{id, label, description}]`.  This converts flat strings to safe defaults.
 */
function ensureObjectArray(
  raw: unknown,
  idPrefix: string,
): Array<Record<string, unknown>> {
  if (!Array.isArray(raw)) return [];
  return raw.map((item, idx) => {
    if (typeof item === "string") {
      return { id: `${idPrefix}_${idx + 1}`, label: item, description: item };
    }
    if (item && typeof item === "object") {
      const obj = item as Record<string, unknown>;
      return {
        id: obj.id || `${idPrefix}_${idx + 1}`,
        label: obj.label || obj.name || String(obj.title || ""),
        description: obj.description || obj.detail || obj.responsibility || "",
        ...obj,
      };
    }
    return {
      id: `${idPrefix}_${idx + 1}`,
      label: String(item),
      description: "",
    };
  });
}

/**
 * Normalize the `visual` dict for a given visual_type so that React
 * components receive data in the shape they expect, even if the LLM
 * produces slightly wrong structures.
 */
function normalizeVisual(
  visualType: string,
  visual: Record<string, unknown>,
): Record<string, unknown> {
  const v = { ...visual };

  // Common pattern: many scene types have a `steps` field that must be
  // an array of objects with {id, label, description}.
  if (
    "steps" in v &&
    visualType !== "algorithm_trace" &&
    visualType !== "cpu_architecture" &&
    visualType !== "memory_layout"
  ) {
    v.steps = ensureObjectArray(v.steps, "step");
  }

  // Type-specific normalizations
  switch (visualType) {
    case "process_flow": {
      v.inputs = Array.isArray(v.inputs) ? v.inputs : [];
      v.outputs = Array.isArray(v.outputs) ? v.outputs : [];
      v.process_name = v.process_name || "";
      v.failure_points = ensureObjectArray(v.failure_points, "fp");
      break;
    }
    case "concept_explain": {
      v.main_concept = v.main_concept || "";
      v.definition = v.definition || "";
      v.keywords = Array.isArray(v.keywords) ? v.keywords : [];
      v.why_it_matters = Array.isArray(v.why_it_matters)
        ? v.why_it_matters
        : [];
      v.related_concepts = ensureObjectArray(v.related_concepts, "rc");
      v.common_misconception = v.common_misconception || "";
      break;
    }
    case "state_machine": {
      v.machine_name = v.machine_name || "";
      v.initial_state = v.initial_state || "";
      v.states = ensureObjectArray(v.states, "st");
      v.transitions = ensureObjectArray(v.transitions, "tr");
      v.event_sequence = ensureObjectArray(v.event_sequence, "ev");
      v.explanation_map =
        v.explanation_map && typeof v.explanation_map === "object"
          ? v.explanation_map
          : {};
      break;
    }
    case "compare_summary": {
      v.compare_title = v.compare_title || "";
      v.left =
        v.left && typeof v.left === "object"
          ? v.left
          : { title: "", points: [] };
      v.right =
        v.right && typeof v.right === "object"
          ? v.right
          : { title: "", points: [] };
      v.same_points = Array.isArray(v.same_points) ? v.same_points : [];
      v.different_points = ensureObjectArray(v.different_points, "diff");
      v.conclusion = v.conclusion || "";
      v.exam_hint = v.exam_hint || "";
      break;
    }
    case "knowledge_check": {
      v.question = v.question || "";
      v.options = ensureObjectArray(v.options, "opt");
      v.correct_answer = v.correct_answer || "";
      v.explanation = v.explanation || "";
      v.related_concept = v.related_concept || "";
      v.review_points = Array.isArray(v.review_points) ? v.review_points : [];
      break;
    }
    case "title_intro": {
      v.course = v.course || "";
      v.chapter = v.chapter || "";
      v.subtitle = v.subtitle || "";
      v.tags = Array.isArray(v.tags) ? v.tags : [];
      v.hero_keywords = Array.isArray(v.hero_keywords) ? v.hero_keywords : [];
      v.hero_center = v.hero_center || "";
      break;
    }
    case "layered_architecture": {
      v.architecture_name = v.architecture_name || "";
      v.layers = ensureObjectArray(v.layers, "layer");
      v.current_focus_layer = v.current_focus_layer || "";
      v.examples = Array.isArray(v.examples) ? v.examples : [];
      break;
    }
    case "network_protocol": {
      v.protocol_name = v.protocol_name || "";
      v.messages = ensureObjectArray(v.messages, "msg");
      v.packet_fields = ensureObjectArray(v.packet_fields, "pf");
      v.state_changes = ensureObjectArray(v.state_changes, "sc");
      v.key_point = v.key_point || "";
      break;
    }
    case "code_execution": {
      v.language = v.language || "python";
      v.code = v.code || "";
      v.output = v.output || "";
      v.error_or_misconception = v.error_or_misconception || "";
      break;
    }
    case "data_structure": {
      v.structure_type = v.structure_type || "linked_list";
      v.initial_state =
        v.initial_state && typeof v.initial_state === "object"
          ? v.initial_state
          : { nodes: [], edges: [] };
      v.operations = ensureObjectArray(v.operations, "op");
      v.pointer_labels = ensureObjectArray(v.pointer_labels, "ptr");
      v.complexity =
        v.complexity && typeof v.complexity === "object"
          ? v.complexity
          : { time: "", space: "" };
      v.invariant = v.invariant || "";
      break;
    }
    case "algorithm_trace": {
      v.algorithm_name = v.algorithm_name || "";
      v.problem = v.problem || "";
      v.data = Array.isArray(v.data) ? v.data : [];
      v.pseudocode = Array.isArray(v.pseudocode) ? v.pseudocode : [];
      v.steps = ensureObjectArray(v.steps, "trace");
      v.complexity =
        v.complexity && typeof v.complexity === "object"
          ? v.complexity
          : { time: "", space: "" };
      v.result = v.result || "";
      break;
    }
    case "memory_layout": {
      v.layout_type = v.layout_type || "stack_heap";
      v.code = v.code || "";
      v.memory_regions = ensureObjectArray(v.memory_regions, "mr");
      v.actions = ensureObjectArray(v.actions, "act");
      v.explanation = v.explanation || "";
      break;
    }
    case "cpu_architecture": {
      v.architecture_name = v.architecture_name || "";
      v.current_instruction = v.current_instruction || "";
      v.modules = ensureObjectArray(v.modules, "mod");
      v.data_paths = ensureObjectArray(v.data_paths, "dp");
      v.steps = ensureObjectArray(v.steps, "cpu_step");
      v.registers = ensureObjectArray(v.registers, "reg");
      v.explanation = v.explanation || "";
      break;
    }
    case "array_linked_list": {
      v.structure_type = v.structure_type || "array";
      v.nodes = ensureObjectArray(v.nodes, "node");
      v.operations = ensureObjectArray(v.operations, "op");
      v.time_complexity = v.time_complexity || "";
      v.space_complexity = v.space_complexity || "";
      break;
    }
    case "stack_queue": {
      v.structure_type = v.structure_type || "stack";
      v.items = ensureObjectArray(v.items, "item");
      v.operations = ensureObjectArray(v.operations, "op");
      break;
    }
    case "process_state": {
      v.states = ensureObjectArray(v.states, "ps");
      v.transitions = ensureObjectArray(v.transitions, "tr");
      break;
    }
    case "storage_hierarchy": {
      v.levels = ensureObjectArray(v.levels, "lvl");
      v.transfers = ensureObjectArray(v.transfers, "xfer");
      v.highlight_level = v.highlight_level || "";
      break;
    }
  }

  return v;
}

/**
 * Safely parse a video plan, returning a structured error message on failure
 * instead of crashing the React render tree.
 */
export function normalizePlan(rawPlan: unknown): RichVideoPlan {
  let plan;
  try {
    plan = videoPlanSchema.parse(rawPlan);
  } catch (e: unknown) {
    const zodErr = e as {
      errors?: Array<{ path: (string | number)[]; message: string }>;
    };
    const details = (zodErr.errors ?? [])
      .slice(0, 5)
      .map((err) => `${err.path.join(".")}: ${err.message}`)
      .join("; ");
    throw new Error(`VideoPlan validation failed: ${details || String(e)}`);
  }

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
      visual: normalizeVisual(scene.visual_type, scene.visual),
      audio_src: scene.audio_src,
      transition: scene.role === "hook" ? "zoom" : "fade",
      caption_words: scene.caption_words,
      caption_chunks: scene.captions,
      visual_cues: scene.visual_cues,
    })),
  };
}
