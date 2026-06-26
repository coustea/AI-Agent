/**
 * Layout Renderers for PptxGenJS
 *
 * 实现各种布局的槽位位置计算和渲染
 */

import pptxgenjs from 'pptxgenjs'
import { slotLayout, spacing, colorPalette, fontSize, fontConfig } from './design-system'
import { renderBlocks } from './block-renderers'
import type { PptSlide, LayoutId, SlideRole } from '../types/ppt'

// PptxGenJS 类型
type PptxGenJS = pptxgenjs
type Slide = pptxgenjs.Slide

/**
 * 布局渲染器：添加标题和副标题
 */
function addSlideHeader(
  slide: Slide,
  title: string,
  subtitle?: string | null
): void {
  // 标题
  slide.addText(title, {
    x: spacing.slidePadding.left,
    y: spacing.slidePadding.top,
    w: 13.333 - spacing.slidePadding.left - spacing.slidePadding.right,
    h: 0.6,
    fontSize: fontSize.slideTitle,
    fontFace: fontConfig.heading.family,
    color: colorPalette.primary,
    bold: true,
    align: 'left',
    valign: 'top',
  })

  // 副标题
  if (subtitle) {
    slide.addText(subtitle, {
      x: spacing.slidePadding.left,
      y: spacing.slidePadding.top + 0.6 + spacing.gap.small,
      w: 13.333 - spacing.slidePadding.left - spacing.slidePadding.right,
      h: 0.4,
      fontSize: fontSize.slideSubtitle,
      fontFace: fontConfig.primary.family,
      color: colorPalette.textSecondary,
      align: 'left',
      valign: 'top',
    })
  }
}

/**
 * HeroCover 布局渲染器
 * - 居中显示标题和副标题
 * - 适用于封面页
 */
export function renderHeroCoverLayout(
  pptx: PptxGenJS,
  slide: Slide,
  pptSlide: PptSlide
): void {
  const layout = slotLayout.HeroCover
  const area = layout.areas.main

  // 封面标题居中
  slide.addText(pptSlide.title, {
    x: area.x,
    y: area.y,
    w: area.w,
    h: 1.2,
    fontSize: 48,
    fontFace: fontConfig.heading.family,
    color: colorPalette.primary,
    bold: true,
    align: 'center',
    valign: 'middle',
  })

  // 副标题
  if (pptSlide.subtitle) {
    slide.addText(pptSlide.subtitle, {
      x: area.x,
      y: area.y + 1.2 + spacing.gap.medium,
      w: area.w,
      h: 0.6,
      fontSize: fontSize.slideSubtitle,
      fontFace: fontConfig.primary.family,
      color: colorPalette.textSecondary,
      align: 'center',
      valign: 'middle',
    })
  }

  // 渲染 main 槽位的 Blocks
  const mainBlocks = pptSlide.slots.main || []
  if (mainBlocks.length > 0) {
    // 封面页的 Blocks 通常在底部
    const blocksArea = {
      x: area.x,
      y: area.y + 2.5,
      w: area.w,
      h: 2,
    }
    renderBlocks(pptx, slide, mainBlocks, blocksArea)
  }
}

/**
 * DualPane 布局渲染器
 * - 左右两栏布局
 * - 适用于概念对比、图文混排
 */
export function renderDualPaneLayout(
  pptx: PptxGenJS,
  slide: Slide,
  pptSlide: PptSlide
): void {
  const layout = slotLayout.DualPane

  // 添加标题
  addSlideHeader(slide, pptSlide.title, pptSlide.subtitle)

  // 渲染左侧 Blocks
  const leftBlocks = pptSlide.slots.left || []
  if (leftBlocks.length > 0) {
    renderBlocks(pptx, slide, leftBlocks, layout.areas.left)
  }

  // 渲染右侧 Blocks
  const rightBlocks = pptSlide.slots.right || []
  if (rightBlocks.length > 0) {
    renderBlocks(pptx, slide, rightBlocks, layout.areas.right)
  }
}

/**
 * TriplePane 布局渲染器
 * - 三栏布局
 * - 适用于机制分解、多维度对比
 */
export function renderTriplePaneLayout(
  pptx: PptxGenJS,
  slide: Slide,
  pptSlide: PptSlide
): void {
  const layout = slotLayout.TriplePane

  // 添加标题
  addSlideHeader(slide, pptSlide.title, pptSlide.subtitle)

  // 渲染左侧 Blocks
  const leftBlocks = pptSlide.slots.left || []
  if (leftBlocks.length > 0) {
    renderBlocks(pptx, slide, leftBlocks, layout.areas.left)
  }

  // 渲染中间 Blocks
  const centerBlocks = pptSlide.slots.center || []
  if (centerBlocks.length > 0) {
    renderBlocks(pptx, slide, centerBlocks, layout.areas.center)
  }

  // 渲染右侧 Blocks
  const rightBlocks = pptSlide.slots.right || []
  if (rightBlocks.length > 0) {
    renderBlocks(pptx, slide, rightBlocks, layout.areas.right)
  }
}

/**
 * DiagramFocus 布局渲染器
 * - 图表为主，右侧注释
 * - 适用于原理图解、架构图
 */
export function renderDiagramFocusLayout(
  pptx: PptxGenJS,
  slide: Slide,
  pptSlide: PptSlide
): void {
  const layout = slotLayout.DiagramFocus

  // 添加标题
  addSlideHeader(slide, pptSlide.title, pptSlide.subtitle)

  // 渲染图表 Blocks
  const diagramBlocks = pptSlide.slots.diagram || []
  if (diagramBlocks.length > 0) {
    renderBlocks(pptx, slide, diagramBlocks, layout.areas.diagram)
  }

  // 渲染注释 Blocks
  const notesBlocks = pptSlide.slots.notes || []
  if (notesBlocks.length > 0) {
    renderBlocks(pptx, slide, notesBlocks, layout.areas.notes)
  }
}

/**
 * FlowCanvas 布局渲染器
 * - 流程图为主，右侧图例
 * - 适用于流程演示、算法可视化
 */
export function renderFlowCanvasLayout(
  pptx: PptxGenJS,
  slide: Slide,
  pptSlide: PptSlide
): void {
  const layout = slotLayout.FlowCanvas

  // 添加标题
  addSlideHeader(slide, pptSlide.title, pptSlide.subtitle)

  // 渲染流程 Blocks
  const flowBlocks = pptSlide.slots.flow || []
  if (flowBlocks.length > 0) {
    renderBlocks(pptx, slide, flowBlocks, layout.areas.flow)
  }

  // 渲染图例 Blocks
  const legendBlocks = pptSlide.slots.legend || []
  if (legendBlocks.length > 0) {
    renderBlocks(pptx, slide, legendBlocks, layout.areas.legend)
  }
}

/**
 * CompareTable 布局渲染器
 * - 表格为主，顶部标题区
 * - 适用于概念对比、数据比较
 */
export function renderCompareTableLayout(
  pptx: PptxGenJS,
  slide: Slide,
  pptSlide: PptSlide
): void {
  const layout = slotLayout.CompareTable

  // 添加标题（简化版，因为表格区域也需要标题）
  slide.addText(pptSlide.title, {
    x: layout.areas.header.x,
    y: layout.areas.header.y,
    w: layout.areas.header.w,
    h: layout.areas.header.h,
    fontSize: fontSize.sectionTitle,
    fontFace: fontConfig.heading.family,
    color: colorPalette.primary,
    bold: true,
    align: 'left',
    valign: 'middle',
  })

  // 渲染表格 Blocks
  const tableBlocks = pptSlide.slots.table || []
  if (tableBlocks.length > 0) {
    renderBlocks(pptx, slide, tableBlocks, layout.areas.table)
  }
}

/**
 * CardCluster 布局渲染器
 * - 卡片群布局
 * - 适用于目标列表、要点总结
 */
export function renderCardClusterLayout(
  pptx: PptxGenJS,
  slide: Slide,
  pptSlide: PptSlide
): void {
  const layout = slotLayout.CardCluster

  // 添加标题
  addSlideHeader(slide, pptSlide.title, pptSlide.subtitle)

  // 渲染卡片 Blocks
  const cardsBlocks = pptSlide.slots.cards || []
  if (cardsBlocks.length > 0) {
    renderBlocks(pptx, slide, cardsBlocks, layout.areas.cards)
  }
}

/**
 * KnowledgeMap 布局渲染器
 * - 知识地图为主，右侧辅助信息
 * - 适用于知识结构、路线图
 */
export function renderKnowledgeMapLayout(
  pptx: PptxGenJS,
  slide: Slide,
  pptSlide: PptSlide
): void {
  const layout = slotLayout.KnowledgeMap

  // 添加标题
  addSlideHeader(slide, pptSlide.title, pptSlide.subtitle)

  // 渲染地图 Blocks
  const mapBlocks = pptSlide.slots.map || []
  if (mapBlocks.length > 0) {
    renderBlocks(pptx, slide, mapBlocks, layout.areas.map)
  }

  // 渲染侧边栏 Blocks
  const sidebarBlocks = pptSlide.slots.sidebar || []
  if (sidebarBlocks.length > 0) {
    renderBlocks(pptx, slide, sidebarBlocks, layout.areas.sidebar)
  }
}

/**
 * 布局渲染器映射
 */
export const layoutRenderers: Record<LayoutId, (pptx: PptxGenJS, slide: Slide, pptSlide: PptSlide) => void> = {
  HeroCover: renderHeroCoverLayout,
  DualPane: renderDualPaneLayout,
  TriplePane: renderTriplePaneLayout,
  DiagramFocus: renderDiagramFocusLayout,
  FlowCanvas: renderFlowCanvasLayout,
  CompareTable: renderCompareTableLayout,
  CardCluster: renderCardClusterLayout,
  KnowledgeMap: renderKnowledgeMapLayout,
}

/**
 * 渲染幻灯片布局
 */
export function renderSlideLayout(
  pptx: PptxGenJS,
  slide: Slide,
  pptSlide: PptSlide
): void {
  const layoutId = pptSlide.layout || 'DualPane'
  const renderer = layoutRenderers[layoutId]

  if (renderer) {
    renderer(pptx, slide, pptSlide)
  } else {
    // 默认使用 DualPane
    renderDualPaneLayout(pptx, slide, pptSlide)
  }
}

/**
 * 根据 Role 推断布局
 */
export function inferLayoutByRole(role: SlideRole): LayoutId {
  const roleLayoutMap: Record<string, LayoutId> = {
    cover: 'HeroCover',
    objectives: 'CardCluster',
    prerequisite: 'DualPane',
    problem_intro: 'DualPane',
    roadmap: 'KnowledgeMap',
    concept: 'DualPane',
    analogy: 'DualPane',
    principle_diagram: 'DiagramFocus',
    process_demo: 'FlowCanvas',
    mechanism_breakdown: 'TriplePane',
    concept_relation: 'DiagramFocus',
    concept_compare: 'CompareTable',
    misconception: 'DualPane',
    summary: 'CardCluster',
    next_steps: 'DualPane',
    algorithm_visualization: 'FlowCanvas',
    code_walkthrough: 'DualPane',
    architecture_diagram: 'DiagramFocus',
  }
  return roleLayoutMap[role] || 'DualPane'
}