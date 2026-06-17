import BlockHeading from './BlockHeading.vue'
import BlockText from './BlockText.vue'
import BlockCallout from './BlockCallout.vue'
import BlockCode from './BlockCode.vue'
import BlockBigNumber from './BlockBigNumber.vue'
import BlockFormula from './BlockFormula.vue'
import BlockTimeline from './BlockTimeline.vue'
import BlockTerminal from './BlockTerminal.vue'

const BlockRegistry: Record<string, any> = {
  Heading: BlockHeading,
  Text: BlockText,
  Callout: BlockCallout,
  Code: BlockCode,
  BigNumber: BlockBigNumber,
  Formula: BlockFormula,
  Timeline: BlockTimeline,
  Terminal: BlockTerminal
}

export const resolveBlock = (type: string) => {
  return BlockRegistry[type] || null
}
