import LayoutFocusTitle from './LayoutFocusTitle.vue'
import LayoutSplitScreen from './LayoutSplitScreen.vue'
import LayoutBentoGrid from './LayoutBentoGrid.vue'
import LayoutLayerStack from './LayoutLayerStack.vue'

export const LayoutRegistry: Record<string, any> = {
  FocusTitle: LayoutFocusTitle,
  SplitScreen: LayoutSplitScreen,
  BentoGrid: LayoutBentoGrid,
  LayerStack: LayoutLayerStack
}

export const resolveLayoutComponent = (layout?: string) => {
  if (!layout) return null
  const component = LayoutRegistry[layout]
  if (!component) {
    console.error(`[PPT Engine] 缺少布局组件: ${layout}`)
    return null
  }
  return component
}
