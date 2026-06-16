import { RichVideoPlan, RichVideoScene, GlobalStyle, RenderConfig, VideoMeta, SceneType } from '../schema/types';

// Default Styles and Configurations
const DEFAULT_GLOBAL_STYLE: GlobalStyle = {
  theme: 'clean_tech_education',
  background: 'soft_grid_gradient',
  primary_color: '#2563eb',
  accent_color: '#3b82f6',
  danger_color: '#ef4444',
  success_color: '#10b981',
  font_family: 'Inter, system-ui, sans-serif',
};

const DEFAULT_RENDER_CONFIG: RenderConfig = {
  width: 1920,
  height: 1080,
  fps: 30,
  format: 'mp4',
  default_scene_transition: 'fade',
  subtitle_enabled: true,
  voiceover_enabled: false,
};

// Valid Union Lists for runtime validation/fallback mapping
const VALID_THEMES = ['clean_tech_education', 'blueprint_academic', 'soft_future_classroom'];
const VALID_BACKGROUNDS = ['soft_grid_gradient', 'circuit_board_light', 'minimal_blueprint'];
const VALID_TRANSITIONS = ['fade', 'slide_left', 'slide_up', 'zoom', 'none'];

/**
 * Normalizes input JSON into the schema format expected by the frontend.
 * Supports both rich_video_plan.json (V2) and backend VideoPayload formats.
 */
export function normalizePlan(rawPlan: any): RichVideoPlan {
  if (!rawPlan) {
    throw new Error('Input video plan is null or undefined');
  }

  const meta: VideoMeta = {
    video_id: rawPlan.meta?.video_id || rawPlan.video_id || 'generated_video',
    title: rawPlan.meta?.title || rawPlan.title || '讲解视频',
    subject: rawPlan.meta?.subject || rawPlan.topic || '计算机理论',
    topic: rawPlan.meta?.topic || rawPlan.topic || '主题讲解',
    difficulty: rawPlan.meta?.difficulty || '基础',
    target_audience: rawPlan.meta?.target_audience || '学生',
    estimated_duration_seconds: rawPlan.meta?.estimated_duration_seconds || rawPlan.duration_seconds || 60,
    language: rawPlan.meta?.language || rawPlan.language || 'zh-CN',
  };

  // Safe mapping of global style
  const rawStyle = rawPlan.global_style || {};
  const theme = VALID_THEMES.includes(rawStyle.theme) ? rawStyle.theme : DEFAULT_GLOBAL_STYLE.theme;
  const background = VALID_BACKGROUNDS.includes(rawStyle.background) ? rawStyle.background : DEFAULT_GLOBAL_STYLE.background;

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
  const default_scene_transition = VALID_TRANSITIONS.includes(rawConfig.default_scene_transition)
    ? rawConfig.default_scene_transition
    : DEFAULT_RENDER_CONFIG.default_scene_transition;

  const renderConfig: RenderConfig = {
    width: rawConfig.width || DEFAULT_RENDER_CONFIG.width,
    height: rawConfig.height || DEFAULT_RENDER_CONFIG.height,
    fps: rawConfig.fps || DEFAULT_RENDER_CONFIG.fps,
    format: rawConfig.format || DEFAULT_RENDER_CONFIG.format,
    default_scene_transition,
    subtitle_enabled: rawConfig.subtitle_enabled ?? DEFAULT_RENDER_CONFIG.subtitle_enabled,
    voiceover_enabled: rawConfig.voiceover_enabled ?? DEFAULT_RENDER_CONFIG.voiceover_enabled,
  };

  const audio = rawPlan.audio || {
    bgm_src: rawPlan.audio?.bgm_src || undefined,
    bgm_volume: rawPlan.audio?.bgm_volume ?? 0.15,
  };

  const scenes: RichVideoScene[] = (rawPlan.scenes || []).map((scene: any, idx: number): RichVideoScene => {
    const id = scene.id || scene.scene_id || `scene_${idx + 1}`;
    const title = scene.title || `分镜 ${idx + 1}`;
    const narration = scene.narration || '';
    const audio_src = scene.audio_src || undefined;
    
    // Parse scene transition
    const transition = VALID_TRANSITIONS.includes(scene.transition)
      ? scene.transition
      : default_scene_transition;

    // Calculate duration in seconds
    let duration_seconds = 8;
    if (typeof scene.duration_seconds === 'number') {
      duration_seconds = scene.duration_seconds;
    } else if (typeof scene.duration_ms === 'number') {
      duration_seconds = scene.duration_ms / 1000;
    } else if (typeof scene.duration === 'number') {
      duration_seconds = scene.duration / 1000;
    }

    // Determine type mapping
    let type = scene.type as SceneType;
    const visualType = scene.visual_type || 'card';

    if (!type) {
      if (idx === 0 && visualType === 'card') {
        type = 'title_intro';
      } else {
        switch (visualType) {
          case 'card':
            type = idx === 0 ? 'title_intro' : 'concept_explain';
            break;
          case 'diagram':
            type = 'concept_explain';
            break;
          case 'code':
            type = 'code_execution';
            break;
          case 'timeline':
            type = 'process_flow';
            break;
          case 'comparison':
            type = 'compare_summary';
            break;
          case 'quiz':
            type = 'knowledge_check';
            break;
          case 'screencast':
            type = 'process_flow';
            break;
          default:
            type = 'concept_explain';
        }
      }
    }

    // Generate or preserve visual data
    let visual = scene.visual;
    if (!visual || typeof visual !== 'object' || Object.keys(visual).length === 0) {
      visual = {};
      const onScreenText: string[] = Array.isArray(scene.on_screen_text) ? scene.on_screen_text : [];
      const visualPrompt = scene.visual_prompt || '';

      if (type === 'title_intro') {
        visual = {
          course: meta.subject,
          chapter: meta.topic,
          subtitle: visualPrompt || title,
          tags: onScreenText.length > 0 ? onScreenText : [meta.topic],
          hero_keywords: onScreenText.length > 0 ? onScreenText : [meta.topic],
        };
      } else if (type === 'concept_explain') {
        visual = {
          main_concept: title,
          definition: visualPrompt || narration,
          keywords: onScreenText.slice(0, 3),
          why_it_matters: onScreenText.length > 0 ? onScreenText : ['直观展示', '加深印象', '核心考点'],
          related_concepts: onScreenText.map((txt) => ({ name: txt, relation: '相关概念' })),
          common_misconception: scene.interaction_prompt || '理解该概念时常产生混淆，需细致辨析。',
        };
      } else if (type === 'process_flow') {
        visual = {
          process_name: title,
          inputs: ['初始状态'],
          outputs: ['结束状态'],
          steps: onScreenText.map((label, stepIdx) => ({
            id: `step_${stepIdx + 1}`,
            label: label,
            description: `步骤 ${stepIdx + 1}: ${label}`,
          })),
          failure_points: [],
        };
      } else if (type === 'code_execution') {
        visual = {
          language: 'python',
          code: onScreenText.join('\n') || '# 演示代码\nprint("Hello, World!")',
          steps: onScreenText.map((line, stepIdx) => ({
            step_index: stepIdx,
            active_line: stepIdx + 1,
            description: `执行: ${line}`,
            variables: [],
            call_stack: ['main'],
          })),
          output: '执行完毕',
          error_or_misconception: scene.interaction_prompt || '',
        };
      } else if (type === 'compare_summary') {
        const half = Math.ceil(onScreenText.length / 2);
        visual = {
          compare_title: title,
          left: {
            title: '方面 A',
            points: onScreenText.slice(0, half),
          },
          right: {
            title: '方面 B',
            points: onScreenText.slice(half),
          },
          same_points: ['同属于当前讨论范畴'],
          different_points: onScreenText.map((pt, pIdx) => ({
            dimension: `特性 ${pIdx + 1}`,
            left: pt,
            right: `对比项 ${pIdx + 1}`,
          })),
          conclusion: visualPrompt || '结论：两者在不同场景下各有优势，应按需选用。',
        };
      } else if (type === 'knowledge_check') {
        const options = onScreenText.length >= 2
          ? onScreenText.map((opt, oIdx) => ({ id: String.fromCharCode(65 + oIdx), text: opt }))
          : [
              { id: 'A', text: '正确' },
              { id: 'B', text: '错误' },
            ];
        visual = {
          question: visualPrompt || title,
          options,
          correct_answer: 'A',
          explanation: narration || '参考旁白解析。',
        };
      } else {
        // Fallback generic card
        visual = {
          title,
          content: visualPrompt || narration,
          points: onScreenText,
        };
      }
    }

    return {
      id,
      type,
      duration_seconds,
      title,
      narration,
      visual,
      audio_src,
      transition: transition as 'fade' | 'slide_left' | 'slide_up' | 'zoom' | 'none',
    };
  });

  return {
    meta,
    global_style: globalStyle,
    render_config: renderConfig,
    audio,
    scenes,
  };
}
