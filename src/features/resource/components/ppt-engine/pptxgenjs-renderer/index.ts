/**
 * PptxGenJS Renderer Module
 *
 * PPT 渲染引擎模块入口
 * 使用 PptxGenJS 直接渲染 PPT，替代 PPTist/Reveal.js 中间层
 */

// 类型定义（从现有类型文件重新导出）
export type {
  PPTDocument,
  PptSlide,
  SlideBlock,
  TextBlock,
  CalloutBlock,
  KeyPointBlock,
  DiagramBlock,
  FlowChartBlock,
  TableBlock,
  CardListBlock,
  FormulaBlock,
  CodeSnippetBlock,
  ThemeType,
  LayoutId,
  SlideRole,
  PptParseResult,
} from '../types/ppt'

// 工具函数（从现有类型文件重新导出）
export {
  parsePptDocument,
  normalizePptDocument,
  inferLayoutByRole,
} from '../types/ppt'

// 渲染函数
export {
  createPresentation,
  renderPPT,
  renderSlide,
  exportPPTX,
  exportPPTXBuffer,
  exportPPTXBase64,
  downloadPPTX,
  renderAndExport,
} from './renderer/index'

// Block 渲染器（高级用法）
export {
  renderBlock,
  renderBlocks,
  blockRenderers,
} from './block-renderers'

// 布局渲染器（高级用法）
export {
  renderSlideLayout,
  layoutRenderers,
  inferLayoutByRole as inferLayout,
} from './layout-renderers'

// 设计系统配置
export {
  colorPalette,
  fontConfig,
  fontSize,
  cornerRadius,
  spacing,
  shapeStyle,
  lineStyle,
  slideSize,
  slotLayout,
  designSystem,
} from './design-system'

// 类型导出
export type { DesignSystem } from './design-system'