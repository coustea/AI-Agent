import LayoutHeroCover from './LayoutHeroCover.vue'
import LayoutDualPane from './LayoutDualPane.vue'
import LayoutTriplePane from './LayoutTriplePane.vue'
import LayoutDiagramFocus from './LayoutDiagramFocus.vue'
import LayoutFlowCanvas from './LayoutFlowCanvas.vue'
import LayoutCompareTable from './LayoutCompareTable.vue'
import LayoutCardCluster from './LayoutCardCluster.vue'
import LayoutKnowledgeMap from './LayoutKnowledgeMap.vue'

const LayoutRegistry: Record<string, any> = {
  HeroCover: LayoutHeroCover,
  DualPane: LayoutDualPane,
  TriplePane: LayoutTriplePane,
  DiagramFocus: LayoutDiagramFocus,
  FlowCanvas: LayoutFlowCanvas,
  CompareTable: LayoutCompareTable,
  CardCluster: LayoutCardCluster,
  KnowledgeMap: LayoutKnowledgeMap,
}

export const resolveLayoutComponent = (layout?: string) => {
  if (!layout) {
    throw new Error(`[PPT Engine] Layout is required`)
  }
  const component = LayoutRegistry[layout]
  if (!component) {
    throw new Error(`[PPT Engine] Unknown layout: ${layout}. Expected one of: ${Object.keys(LayoutRegistry).join(', ')}`)
  }
  return component
}
