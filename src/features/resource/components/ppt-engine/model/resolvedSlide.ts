import type { SlideRole, ContentElement, Relation } from './slideIntent'

export interface ResolvedSlide {
  id: string
  index: number
  role: SlideRole
  title: string
  key_message: string
  theme_id: 'technical-blueprint' | 'editorial-academic' | 'modern-classroom'
  composition_id:
    | 'TheoryCover'
    | 'SectionBreak'
    | 'DefinitionFocus'
    | 'ConceptBreakdown'
    | 'HierarchyMap'
    | 'ComponentArchitecture'
    | 'StateTransition'
    | 'SequenceTimeline'
    | 'DataFlow'
    | 'ProtocolStack'
    | 'AlgorithmProcess'
    | 'Comparison'
    | 'CauseEffect'
    | 'WorkedExample'
    | 'KnowledgeMap'
    | 'ChapterSummary'
  elements: ContentElement[]
  relations?: Relation[]
  density: 'light' | 'medium' | 'dense'
  slots: Record<string, ContentElement[]>
  speaker_notes?: string
  coordinates?: Record<string, { left: number; top: number; width: number; height: number }>
}
