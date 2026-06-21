import BlockText from './BlockText.vue'
import BlockCallout from './BlockCallout.vue'
import BlockKeyPoint from './BlockKeyPoint.vue'
import BlockDiagram from './BlockDiagram.vue'
import BlockFlowChart from './BlockFlowChart.vue'
import BlockTable from './BlockTable.vue'
import BlockCardList from './BlockCardList.vue'
import BlockFormula from './BlockFormula.vue'
import BlockCodeSnippet from './BlockCodeSnippet.vue'

const BlockRegistry: Record<string, any> = {
  Text: BlockText,
  Callout: BlockCallout,
  KeyPoint: BlockKeyPoint,
  Diagram: BlockDiagram,
  FlowChart: BlockFlowChart,
  Table: BlockTable,
  CardList: BlockCardList,
  Formula: BlockFormula,
  CodeSnippet: BlockCodeSnippet,
}

export const resolveBlock = (type: string) => {
  const component = BlockRegistry[type]
  if (!component) {
    throw new Error(`[PPT Engine] Unknown block: ${type}. Expected one of: ${Object.keys(BlockRegistry).join(', ')}`)
  }
  return component
}
