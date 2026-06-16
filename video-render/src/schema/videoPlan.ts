export type ComputerCourse =
  | 'data_structure'
  | 'operating_system'
  | 'network'
  | 'programming'
  | 'common';

export type RenderMode = 'quick' | 'standard' | 'detailed';

export type TemplateName =
  | 'concept_explain'
  | 'process_flow'
  | 'code_walkthrough'
  | 'question_solution'
  | 'summary_card'
  | 'comparison_table'
  | 'linear_structure_demo'
  | 'linked_list_demo'
  | 'tree_graph_traversal'
  | 'process_state_transition'
  | 'cpu_scheduling_demo'
  | 'protocol_sequence'
  | 'call_stack_demo';

export type TeachingVideoPlan = {
  resource_type: 'computer_teaching_video';
  title: string;
  course: ComputerCourse;
  knowledge_point: string;
  knowledge_type: string;
  video_config: {
    mode: RenderMode;
    duration_seconds: number;
    fps: 24 | 30;
    resolution: '1280x720' | '1920x1080';
    ratio: '16:9';
    renderer: 'motion_canvas';
    export_format: 'mp4';
    voice?: boolean;
    subtitle?: boolean;
  };
  user_config?: {
    explain_depth?: 'basic' | 'exam' | 'advanced';
    prefer_examples?: boolean;
    prefer_code?: boolean;
    prefer_exam_focus?: boolean;
    programming_language?: 'python' | 'cpp' | 'java' | 'javascript' | 'sql';
    style?: 'clean' | 'classroom' | 'card';
  };
  teaching_goal: string;
  scenes: TeachingVideoScene[];
  quality_constraints?: {
    must_include?: string[];
    avoid?: string[];
  };
};

export type TeachingVideoScene = {
  id: string;
  stage:
    | 'intro'
    | 'concept'
    | 'mechanism'
    | 'animation'
    | 'code'
    | 'example'
    | 'comparison'
    | 'warning'
    | 'summary';
  template: TemplateName;
  duration_seconds: number;
  title: string;
  narration?: string;
  subtitle?: string;
  render_budget?: {
    complexity: 'low' | 'medium' | 'high';
    max_animation_steps?: number;
    max_items?: number;
  };
  visual_data: Record<string, any>;
};
