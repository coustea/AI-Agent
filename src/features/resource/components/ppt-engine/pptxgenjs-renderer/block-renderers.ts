/**
 * Block Renderers for PptxGenJS
 *
 * 将 9 种 Block 类型映射到 PptxGenJS API
 */

import pptxgenjs from 'pptxgenjs'
import {
  colorPalette,
  fontSize,
  spacing,
  shapeStyle,
  lineStyle,
  fontConfig,
} from './design-system'
import type {
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
} from '../types/ppt'

// PptxGenJS 类型
type PptxGenJS = pptxgenjs
type Slide = pptxgenjs.Slide

// 渲染上下文
interface RenderContext {
  pptx: PptxGenJS
  slide: Slide
  area: { x: number; y: number; w: number; h: number }
}

// 形状常量 - 使用字符串值作为 SHAPE_NAME 类型
const SHAPES = {
  RECTANGLE: 'rect' as pptxgenjs.SHAPE_NAME,
  ROUNDED_RECTANGLE: 'roundRect' as pptxgenjs.SHAPE_NAME,
  LINE: 'line' as pptxgenjs.SHAPE_NAME,
  DOWN_ARROW: 'downArrow' as pptxgenjs.SHAPE_NAME,
}

/**
 * 渲染 Text Block
 */
export function renderTextBlock(ctx: RenderContext, block: TextBlock): void {
  const { slide, area } = ctx

  // 处理 markdown 格式（简化处理）
  let content = block.content
  if (block.format === 'markdown') {
    content = content
      .replace(/\*\*(.*?)\*\*/g, '$1')
      .replace(/\*(.*?)\*/g, '$1')
      .replace(/`(.*?)`/g, '$1')
  }

  slide.addText(content, {
    x: area.x,
    y: area.y,
    w: area.w,
    h: area.h,
    fontSize: fontSize.body,
    fontFace: fontConfig.primary.family,
    color: colorPalette.textPrimary,
    align: 'left',
    valign: 'top',
    wrap: true,
  })
}

/**
 * 渲染 KeyPoint Block
 */
export function renderKeyPointBlock(ctx: RenderContext, block: KeyPointBlock): void {
  const { slide, area } = ctx
  const style = shapeStyle.keyPoint

  // 创建背景形状
  slide.addShape(SHAPES.ROUNDED_RECTANGLE, {
    x: area.x,
    y: area.y,
    w: area.w,
    h: area.h,
    fill: { color: style.fill },
    line: { color: style.stroke, width: style.strokeWidth },
    rectRadius: style.cornerRadius,
  })

  // 添加标签
  const labelHeight = 0.3
  slide.addText(block.label, {
    x: area.x + spacing.padding.medium,
    y: area.y + spacing.padding.medium,
    w: area.w - spacing.padding.medium * 2,
    h: labelHeight,
    fontSize: fontSize.keyPointLabel,
    fontFace: fontConfig.primary.family,
    color: colorPalette.accent,
    bold: true,
    align: 'left',
    valign: 'middle',
  })

  // 添加内容
  slide.addText(block.content, {
    x: area.x + spacing.padding.medium,
    y: area.y + labelHeight + spacing.padding.medium + spacing.gap.small,
    w: area.w - spacing.padding.medium * 2,
    h: area.h - labelHeight - spacing.padding.medium * 2 - spacing.gap.small,
    fontSize: fontSize.keyPointContent,
    fontFace: fontConfig.primary.family,
    color: colorPalette.textPrimary,
    align: 'left',
    valign: 'top',
    wrap: true,
  })
}

/**
 * 渲染 Callout Block
 */
export function renderCalloutBlock(ctx: RenderContext, block: CalloutBlock): void {
  const { slide, area } = ctx
  const intentStyle = shapeStyle.callout[block.intent] || shapeStyle.callout.info

  // 创建背景形状
  slide.addShape(SHAPES.ROUNDED_RECTANGLE, {
    x: area.x,
    y: area.y,
    w: area.w,
    h: area.h,
    fill: { color: intentStyle.fill },
    line: { color: intentStyle.stroke, width: intentStyle.strokeWidth },
    rectRadius: intentStyle.cornerRadius,
  })

  // 添加图标和标题
  const iconMap: Record<string, string> = {
    info: '💡',
    warning: '⚠️',
    success: '✅',
    danger: '❌',
  }
  const icon = iconMap[block.icon] || '💡'

  slide.addText(`${icon} ${block.intent.toUpperCase()}`, {
    x: area.x + spacing.padding.medium,
    y: area.y + spacing.padding.medium,
    w: area.w - spacing.padding.medium * 2,
    h: 0.35,
    fontSize: fontSize.calloutTitle,
    fontFace: fontConfig.primary.family,
    color: intentStyle.stroke,
    bold: true,
    align: 'left',
    valign: 'middle',
  })

  // 添加内容
  slide.addText(block.content, {
    x: area.x + spacing.padding.medium,
    y: area.y + 0.35 + spacing.padding.medium + spacing.gap.small,
    w: area.w - spacing.padding.medium * 2,
    h: area.h - 0.35 - spacing.padding.medium * 2 - spacing.gap.small,
    fontSize: fontSize.calloutContent,
    fontFace: fontConfig.primary.family,
    color: colorPalette.textPrimary,
    align: 'left',
    valign: 'top',
    wrap: true,
  })
}

/**
 * 渲染 Diagram Block
 */
export function renderDiagramBlock(ctx: RenderContext, block: DiagramBlock): void {
  const { slide, area } = ctx
  const { nodes, edges, direction } = block

  if (nodes.length < 2) return

  // 计算节点位置
  const nodePositions = calculateNodePositions(nodes, area, direction)

  // 渲染节点
  for (const node of nodes) {
    const pos = nodePositions[node.id]
    if (!pos) continue

    // 绘制节点形状
    slide.addShape(SHAPES.ROUNDED_RECTANGLE, {
      x: pos.x,
      y: pos.y,
      w: pos.w,
      h: pos.h,
      fill: { color: shapeStyle.diagramNode.fill },
      line: { color: shapeStyle.diagramNode.stroke, width: shapeStyle.diagramNode.strokeWidth },
      rectRadius: shapeStyle.diagramNode.cornerRadius,
    })

    // 绘制节点标签
    slide.addText(node.label, {
      x: pos.x,
      y: pos.y,
      w: pos.w,
      h: pos.h,
      fontSize: fontSize.diagramLabel,
      fontFace: fontConfig.primary.family,
      color: colorPalette.textPrimary,
      align: 'center',
      valign: 'middle',
      wrap: true,
    })
  }

  // 渲染连接线
  for (const edge of edges) {
    const sourcePos = nodePositions[edge.source]
    const targetPos = nodePositions[edge.target]
    if (!sourcePos || !targetPos) continue

    const lineCoords = calculateEdgeCoordinates(sourcePos, targetPos, direction)

    slide.addShape(SHAPES.LINE, {
      x: lineCoords.x,
      y: lineCoords.y,
      w: lineCoords.w,
      h: lineCoords.h,
      line: {
        color: lineStyle.arrow.color,
        width: lineStyle.arrow.width,
        endArrowType: 'triangle',
      },
    })

    // 如果有标签，添加连接线标签
    if (edge.label) {
      const labelX = lineCoords.x + lineCoords.w / 2 - 0.5
      const labelY = lineCoords.y + lineCoords.h / 2 - 0.15

      slide.addText(edge.label, {
        x: labelX,
        y: labelY,
        w: 1,
        h: 0.3,
        fontSize: fontSize.caption,
        fontFace: fontConfig.primary.family,
        color: colorPalette.textSecondary,
        align: 'center',
        valign: 'middle',
      })
    }
  }
}

/**
 * 计算节点位置
 */
function calculateNodePositions(
  nodes: DiagramBlock['nodes'],
  area: RenderContext['area'],
  direction: DiagramBlock['direction']
): Record<string, { x: number; y: number; w: number; h: number }> {
  const nodeWidth = 1.5
  const nodeHeight = 0.6
  const gap = spacing.gap.medium

  const positions: Record<string, { x: number; y: number; w: number; h: number }> = {}

  if (direction === 'LR' || direction === 'RL') {
    const startX = direction === 'LR' ? area.x : area.x + area.w - nodeWidth
    const startY = area.y + (area.h - nodeHeight) / 2

    nodes.forEach((node, i) => {
      const x = direction === 'LR'
        ? startX + i * (nodeWidth + gap)
        : startX - i * (nodeWidth + gap)
      positions[node.id] = { x, y: startY, w: nodeWidth, h: nodeHeight }
    })
  } else {
    const startY = direction === 'TB' ? area.y : area.y + area.h - nodeHeight
    const startX = area.x + (area.w - nodeWidth) / 2

    nodes.forEach((node, i) => {
      const y = direction === 'TB'
        ? startY + i * (nodeHeight + gap)
        : startY - i * (nodeHeight + gap)
      positions[node.id] = { x: startX, y, w: nodeWidth, h: nodeHeight }
    })
  }

  return positions
}

/**
 * 计算连接线坐标
 */
function calculateEdgeCoordinates(
  source: { x: number; y: number; w: number; h: number },
  target: { x: number; y: number; w: number; h: number },
  direction: DiagramBlock['direction']
): { x: number; y: number; w: number; h: number } {
  if (direction === 'LR') {
    return {
      x: source.x + source.w,
      y: source.y + source.h / 2,
      w: target.x - source.x - source.w,
      h: 0,
    }
  } else if (direction === 'RL') {
    return {
      x: target.x + target.w,
      y: target.y + target.h / 2,
      w: source.x - target.x - target.w,
      h: 0,
    }
  } else if (direction === 'TB') {
    return {
      x: source.x + source.w / 2,
      y: source.y + source.h,
      w: 0,
      h: target.y - source.y - source.h,
    }
  } else {
    return {
      x: target.x + target.w / 2,
      y: target.y + target.h,
      w: 0,
      h: source.y - target.y - target.h,
    }
  }
}

/**
 * 渲染 FlowChart Block
 */
export function renderFlowChartBlock(ctx: RenderContext, block: FlowChartBlock): void {
  const { slide, area } = ctx
  const { steps } = block

  if (steps.length < 2) return

  const stepHeight = 1.0
  const stepWidth = area.w
  const gap = spacing.gap.medium
  const totalHeight = steps.length * stepHeight + (steps.length - 1) * gap

  const startY = area.y + Math.max(0, (area.h - totalHeight) / 2)

  steps.forEach((step, i) => {
    const y = startY + i * (stepHeight + gap)
    const x = area.x

    // 绘制步骤形状
    slide.addShape(SHAPES.ROUNDED_RECTANGLE, {
      x: x,
      y: y,
      w: stepWidth,
      h: stepHeight,
      fill: { color: shapeStyle.flowStep.fill },
      line: { color: shapeStyle.flowStep.stroke, width: shapeStyle.flowStep.strokeWidth },
      rectRadius: shapeStyle.flowStep.cornerRadius,
    })

    // 绘制步骤标题
    slide.addText(step.title, {
      x: x + spacing.padding.medium,
      y: y + spacing.padding.small,
      w: stepWidth - spacing.padding.medium * 2,
      h: 0.25,
      fontSize: fontSize.flowStepTitle,
      fontFace: fontConfig.primary.family,
      color: colorPalette.accent,
      bold: true,
      align: 'left',
      valign: 'middle',
    })

    // 绘制步骤描述
    slide.addText(step.description, {
      x: x + spacing.padding.medium,
      y: y + 0.25 + spacing.padding.small,
      w: stepWidth - spacing.padding.medium * 2,
      h: stepHeight - 0.25 - spacing.padding.small * 2,
      fontSize: fontSize.flowStepDesc,
      fontFace: fontConfig.primary.family,
      color: colorPalette.textSecondary,
      align: 'left',
      valign: 'top',
      wrap: true,
    })

    // 绘制连接箭头
    if (i < steps.length - 1) {
      const arrowY = y + stepHeight
      const arrowH = gap

      slide.addShape(SHAPES.DOWN_ARROW, {
        x: x + stepWidth / 2 - 0.15,
        y: arrowY,
        w: 0.3,
        h: arrowH,
        fill: { color: lineStyle.connector.color },
      })
    }
  })
}

/**
 * 渲染 Table Block
 */
export function renderTableBlock(ctx: RenderContext, block: TableBlock): void {
  const { slide, area } = ctx
  const { columns, rows } = block

  // 构建表格数据 - 使用正确的 fill 格式
  const tableData: pptxgenjs.TableRow[] = []

  // 表头
  tableData.push(columns.map(col => ({
    text: col,
    options: {
      bold: true,
      fill: { color: colorPalette.primary },
      color: colorPalette.textOnPrimary,
      fontSize: fontSize.tableHeader,
      fontFace: fontConfig.primary.family,
      align: 'center',
      valign: 'middle',
    },
  })))

  // 表格行
  rows.forEach(row => {
    tableData.push(row.map(cell => ({
      text: cell,
      options: {
        fill: { color: colorPalette.cardBackground },
        color: colorPalette.textPrimary,
        fontSize: fontSize.tableCell,
        fontFace: fontConfig.primary.family,
        align: 'center',
        valign: 'middle',
      },
    })))
  })

  // 计算列宽
  const colW = columns.map(() => area.w / columns.length)

  slide.addTable(tableData, {
    x: area.x,
    y: area.y,
    w: area.w,
    colW: colW,
    border: { pt: 1, color: colorPalette.border },
    fontFace: fontConfig.primary.family,
    fontSize: fontSize.tableCell,
    align: 'center',
    valign: 'middle',
  })
}

/**
 * 渲染 CardList Block
 */
export function renderCardListBlock(ctx: RenderContext, block: CardListBlock): void {
  const { slide, area } = ctx
  const { cards } = block

  if (cards.length === 0) return

  const cardWidth = Math.min(3.5, (area.w - (cards.length - 1) * spacing.gap.medium) / cards.length)
  const cardHeight = area.h
  const startX = area.x

  cards.forEach((card, i) => {
    const x = startX + i * (cardWidth + spacing.gap.medium)
    const y = area.y

    // 绘制卡片形状
    slide.addShape(SHAPES.ROUNDED_RECTANGLE, {
      x: x,
      y: y,
      w: cardWidth,
      h: cardHeight,
      fill: { color: shapeStyle.card.fill },
      line: { color: shapeStyle.card.stroke, width: shapeStyle.card.strokeWidth },
      rectRadius: shapeStyle.card.cornerRadius,
    })

    // 绘制卡片标题
    const titleHeight = 0.4
    slide.addText(card.title, {
      x: x + spacing.padding.card,
      y: y + spacing.padding.card,
      w: cardWidth - spacing.padding.card * 2,
      h: titleHeight,
      fontSize: fontSize.cardTitle,
      fontFace: fontConfig.primary.family,
      color: colorPalette.primary,
      bold: true,
      align: 'left',
      valign: 'middle',
    })

    // 绘制卡片内容
    slide.addText(card.content, {
      x: x + spacing.padding.card,
      y: y + titleHeight + spacing.padding.card + spacing.gap.small,
      w: cardWidth - spacing.padding.card * 2,
      h: cardHeight - titleHeight - spacing.padding.card * 2 - spacing.gap.small,
      fontSize: fontSize.cardContent,
      fontFace: fontConfig.primary.family,
      color: colorPalette.textSecondary,
      align: 'left',
      valign: 'top',
      wrap: true,
    })
  })
}

/**
 * 渲染 Formula Block
 */
export function renderFormulaBlock(ctx: RenderContext, block: FormulaBlock): void {
  const { slide, area } = ctx
  const style = shapeStyle.formula

  // 创建背景形状
  slide.addShape(SHAPES.ROUNDED_RECTANGLE, {
    x: area.x,
    y: area.y + (area.h - 0.8) / 2,
    w: area.w,
    h: 0.8,
    fill: { color: style.fill },
    line: { color: style.stroke, width: style.strokeWidth },
    rectRadius: style.cornerRadius,
  })

  // 添加公式文本
  slide.addText(block.formula, {
    x: area.x,
    y: area.y + (area.h - 0.8) / 2,
    w: area.w,
    h: 0.8,
    fontSize: fontSize.formula,
    fontFace: fontConfig.mono.family,
    color: colorPalette.primary,
    align: 'center',
    valign: 'middle',
  })
}

/**
 * 渲染 CodeSnippet Block
 */
export function renderCodeSnippetBlock(ctx: RenderContext, block: CodeSnippetBlock): void {
  const { slide, area } = ctx
  const { code, language, highlights } = block

  const codeLines = code.split('\n')
  const lineHeight = 0.25
  const padding = spacing.padding.medium
  const headerHeight = 0.35

  const totalHeight = headerHeight + codeLines.length * lineHeight + padding * 2
  const blockHeight = Math.min(totalHeight, area.h)

  // 绘制代码块背景
  slide.addShape(SHAPES.ROUNDED_RECTANGLE, {
    x: area.x,
    y: area.y,
    w: area.w,
    h: blockHeight,
    fill: { color: shapeStyle.codeBlock.fill },
    rectRadius: shapeStyle.codeBlock.cornerRadius,
  })

  // 绘制语言标签
  slide.addText(language.toUpperCase(), {
    x: area.x + padding,
    y: area.y + padding,
    w: area.w - padding * 2,
    h: headerHeight - padding,
    fontSize: fontSize.label,
    fontFace: fontConfig.mono.family,
    color: colorPalette.accent,
    bold: true,
    align: 'left',
    valign: 'middle',
  })

  // 绘制代码内容（带行号）
  const codeContent = codeLines.map((line, i) => {
    const lineNum = `${i + 1}`.padStart(3, ' ')
    return `${lineNum}  ${line}`
  }).join('\n')

  slide.addText(codeContent, {
    x: area.x + padding,
    y: area.y + headerHeight + padding,
    w: area.w - padding * 2,
    h: blockHeight - headerHeight - padding * 2,
    fontSize: fontSize.codeBlock,
    fontFace: fontConfig.mono.family,
    color: colorPalette.codeText,
    align: 'left',
    valign: 'top',
    wrap: false,
  })

  // 绘制高亮行标记
  highlights.forEach(highlight => {
    const highlightY = area.y + headerHeight + padding + (highlight.line - 1) * lineHeight
    if (highlightY < area.y + blockHeight - padding) {
      slide.addShape(SHAPES.RECTANGLE, {
        x: area.x,
        y: highlightY,
        w: area.w,
        h: lineHeight,
        fill: { color: colorPalette.accent, transparency: 70 },
      })
    }
  })
}

/**
 * Block 渲染器映射
 */
export const blockRenderers: Record<SlideBlock['type'], (ctx: RenderContext, block: SlideBlock) => void> = {
  Text: renderTextBlock as (ctx: RenderContext, block: SlideBlock) => void,
  KeyPoint: renderKeyPointBlock as (ctx: RenderContext, block: SlideBlock) => void,
  Callout: renderCalloutBlock as (ctx: RenderContext, block: SlideBlock) => void,
  Diagram: renderDiagramBlock as (ctx: RenderContext, block: SlideBlock) => void,
  FlowChart: renderFlowChartBlock as (ctx: RenderContext, block: SlideBlock) => void,
  Table: renderTableBlock as (ctx: RenderContext, block: SlideBlock) => void,
  CardList: renderCardListBlock as (ctx: RenderContext, block: SlideBlock) => void,
  Formula: renderFormulaBlock as (ctx: RenderContext, block: SlideBlock) => void,
  CodeSnippet: renderCodeSnippetBlock as (ctx: RenderContext, block: SlideBlock) => void,
}

/**
 * 渲染单个 Block
 */
export function renderBlock(ctx: RenderContext, block: SlideBlock): void {
  const renderer = blockRenderers[block.type]
  if (renderer) {
    renderer(ctx, block)
  }
}

/**
 * 渲染多个 Blocks
 */
export function renderBlocks(
  pptx: PptxGenJS,
  slide: Slide,
  blocks: SlideBlock[],
  area: { x: number; y: number; w: number; h: number }
): void {
  if (blocks.length === 0) return

  if (blocks.length === 1) {
    renderBlock({ pptx, slide, area }, blocks[0]!)
    return
  }

  const blockHeight = area.h / blocks.length
  const gap = spacing.gap.small

  blocks.forEach((block, i) => {
    const blockArea = {
      x: area.x,
      y: area.y + i * blockHeight + (i > 0 ? gap / 2 : 0),
      w: area.w,
      h: blockHeight - (i > 0 && i < blocks.length - 1 ? gap : 0),
    }
    renderBlock({ pptx, slide, area: blockArea }, block!)
  })
}