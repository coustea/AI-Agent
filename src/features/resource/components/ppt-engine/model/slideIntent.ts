export interface ContentElement {
  type:
    | 'concept'
    | 'definition'
    | 'statement'
    | 'step'
    | 'entity'
    | 'metric'
    | 'hierarchy_node'
    | 'state_node'
    | 'sequence_participant'
    | 'process_node'
    | 'formula'
    | 'image'
    | 'icon'
    | 'table'
    | 'quote'
    | 'code'
  content?: string
  label?: string
  properties?: any
}

export interface Relation {
  type:
    | 'parent_child'
    | 'dependency'
    | 'transition'
    | 'sequence'
    | 'data_flow'
    | 'comparison'
    | 'cause_effect'
    | 'association'
  source: string
  target: string
  label?: string
}

export type SlideRole =
  | 'cover'
  | 'section'
  | 'definition'
  | 'concept'
  | 'hierarchy'
  | 'architecture'
  | 'state_transition'
  | 'sequence'
  | 'data_flow'
  | 'protocol_stack'
  | 'process'
  | 'comparison'
  | 'cause_effect'
  | 'worked_example'
  | 'knowledge_map'
  | 'ending'
  | 'objectives'
  | 'prerequisite'
  | 'problem_intro'
  | 'roadmap'
  | 'analogy'
  | 'principle_diagram'
  | 'process_demo'
  | 'mechanism_breakdown'
  | 'concept_relation'
  | 'concept_compare'
  | 'misconception'
  | 'summary'
  | 'next_steps'
  | 'algorithm_visualization'
  | 'code_walkthrough'
  | 'architecture_diagram'

export interface SlideIntent {
  id: string
  role: SlideRole
  title: string
  key_message: string
  elements: ContentElement[]
  relations?: Relation[]
  density: 'light' | 'medium' | 'dense'
  visual_hints?: Record<string, any>
}

export interface PptDocument {
  template_id: 'teaching-lesson'
  theme_id: 'technical-blueprint' | 'editorial-academic' | 'modern-classroom'
  explanation_style: 'conceptual' | 'procedural' | 'comparative'
  visual_emphasis: 'minimal' | 'balanced' | 'rich'
  title: string
  audience: string
  slides: SlideIntent[]
}
