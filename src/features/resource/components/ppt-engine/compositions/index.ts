import TheoryCover from './TheoryCover.vue'
import SectionBreak from './SectionBreak.vue'
import DefinitionFocus from './DefinitionFocus.vue'
import ConceptBreakdown from './ConceptBreakdown.vue'
import HierarchyMap from './HierarchyMap.vue'
import ComponentArchitecture from './ComponentArchitecture.vue'
import StateTransition from './StateTransition.vue'
import SequenceTimeline from './SequenceTimeline.vue'
import DataFlow from './DataFlow.vue'
import ProtocolStack from './ProtocolStack.vue'
import AlgorithmProcess from './AlgorithmProcess.vue'
import Comparison from './Comparison.vue'
import CauseEffect from './CauseEffect.vue'
import WorkedExample from './WorkedExample.vue'
import KnowledgeMap from './KnowledgeMap.vue'
import ChapterSummary from './ChapterSummary.vue'

export const Compositions: Record<string, any> = {
  TheoryCover,
  SectionBreak,
  DefinitionFocus,
  ConceptBreakdown,
  HierarchyMap,
  ComponentArchitecture,
  StateTransition,
  SequenceTimeline,
  DataFlow,
  ProtocolStack,
  AlgorithmProcess,
  Comparison,
  CauseEffect,
  WorkedExample,
  KnowledgeMap,
  ChapterSummary
}

export const resolveComposition = (id: string) => {
  const component = Compositions[id]
  if (!component) {
    return ConceptBreakdown
  }
  return component
}
