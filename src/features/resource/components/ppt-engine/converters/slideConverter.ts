/**
 * PPT数据转换器 - 将后端PptDocument转换为PPTist Slide格式
 * 专门用于计算机理论教学PPT
 */

import type { PPTDocument, PptSlide, SlideBlock, LayoutId, DiagramBlock, FlowChartBlock } from '../types/ppt'
import type { PPTSlide, PPTElement } from 'pptist'

/**
 * 纸墨白护眼主题配置 (对应默认的 paper-light)
 */
export const whiteTheme = {
  backgroundColor: '#FAF9F6',
  themeColors: ['#2563EB', '#3B82F6', '#60A5FA'], // 蓝色系
  fontColor: '#0F172A',
  fontName: 'Source Sans Pro',
}

/**
 * Layout槽位位置映射
 * 将固定布局的槽位转换为PPTist元素的绝对坐标 (与 Vue Layout 比例一致)
 */
function getSlotPosition(
  layout: LayoutId,
  slotName: string,
  _index: number
): { left: number; top: number; width: number; height: number } {
  const baseWidth = 1280
  const baseHeight = 720
  const padding = 36
  const headerHeight = 90
  const footerHeight = 70
  const contentHeight = baseHeight - headerHeight - footerHeight
  const contentWidth = baseWidth - padding * 2

  const positions: Record<LayoutId, Record<string, any>> = {
    HeroCover: {
      main: { left: padding + 100, top: headerHeight + 50, width: contentWidth - 200, height: contentHeight - 100 },
    },
    DualPane: {
      left: { left: padding, top: headerHeight, width: contentWidth * 0.62 - 18, height: contentHeight },
      right: { left: padding + contentWidth * 0.62 + 18, top: headerHeight, width: contentWidth * 0.38 - 18, height: contentHeight },
    },
    TriplePane: {
      left: { left: padding, top: headerHeight, width: 430, height: contentHeight },
      center: { left: padding + 430 + 28, top: headerHeight, width: 380, height: contentHeight },
      right: { left: padding + 430 + 28 + 380 + 28, top: headerHeight, width: 342, height: contentHeight },
    },
    DiagramFocus: {
      diagram: { left: padding, top: headerHeight, width: contentWidth * 0.68 - 18, height: contentHeight },
      explanation: { left: padding + contentWidth * 0.68 + 18, top: headerHeight, width: contentWidth * 0.32 - 18, height: contentHeight },
    },
    FlowCanvas: {
      flow: { left: padding, top: headerHeight, width: contentWidth * 0.65 - 18, height: contentHeight },
      annotation: { left: padding + contentWidth * 0.65 + 18, top: headerHeight, width: contentWidth * 0.35 - 18, height: contentHeight },
    },
    CompareTable: {
      comparison: { left: padding, top: headerHeight, width: contentWidth * 0.70 - 18, height: contentHeight },
      insight: { left: padding + contentWidth * 0.70 + 18, top: headerHeight, width: contentWidth * 0.30 - 18, height: contentHeight },
    },
    CardCluster: {
      featured: { left: padding, top: headerHeight, width: contentWidth * 0.35 - 18, height: contentHeight },
      cards: { left: padding + contentWidth * 0.35 + 18, top: headerHeight, width: contentWidth * 0.65 - 18, height: contentHeight },
    },
    KnowledgeMap: {
      map: { left: padding, top: headerHeight, width: contentWidth * 0.68 - 18, height: contentHeight },
      legend: { left: padding + contentWidth * 0.68 + 18, top: headerHeight, width: contentWidth * 0.32 - 18, height: contentHeight },
    },
  }

  return positions[layout]?.[slotName] || { left: padding, top: headerHeight, width: contentWidth, height: contentHeight }
}

/**
 * 转换单个Block为PPTist Element
 * 支持所有9种Block类型的可视化渲染，样式与 Vue blocks 高度同步
 */
function convertBlockToElement(
  block: SlideBlock,
  position: { left: number; top: number; width: number; height: number }
): PPTElement {
  const baseElement = {
    id: block.block_id,
    left: position.left,
    top: position.top,
    width: position.width,
    height: position.height,
    rotate: 0,
  }

  switch (block.type) {
    case 'Text':
      return {
        ...baseElement,
        type: 'text',
        content: `<p style="font-size: 18px; line-height: 1.7; color: #475569; margin: 0; font-family: 'Inter', sans-serif;">${block.content}</p>`,
        defaultFontName: whiteTheme.fontName,
        defaultColor: whiteTheme.fontColor,
      }

    case 'KeyPoint':
      return {
        ...baseElement,
        type: 'text',
        content: `
          <div style="background: linear-gradient(135deg, #FFFFFF 0%, rgba(37, 99, 235, 0.03) 100%); border: 1px solid rgba(37, 99, 235, 0.08); padding: 24px; border-radius: 14px; box-shadow: 0 10px 30px rgba(15, 23, 42, 0.04); font-family: 'Inter', sans-serif;">
            <div style="display: flex; align-items: center; margin-bottom: 12px;">
              <span style="width: 8px; height: 8px; border-radius: 50%; background: #2563EB; display: inline-block; margin-right: 8px;"></span>
              <span style="font-size: 14px; color: #2563EB; font-weight: 800; letter-spacing: 0.1em; text-transform: uppercase;">${block.label}</span>
            </div>
            <p style="font-size: 24px; color: #0F172A; font-weight: 800; margin: 0; line-height: 1.4;">${block.content}</p>
          </div>
        `,
        defaultFontName: whiteTheme.fontName,
        defaultColor: whiteTheme.fontColor,
      }

    case 'CardList':
      const cardsHtml = block.cards.map(card => `
        <div style="background: #FFFFFF; border: 1px solid rgba(37, 99, 235, 0.08); border-radius: 14px; padding: 20px; margin-bottom: 16px; box-shadow: 0 10px 30px rgba(15, 23, 42, 0.04); font-family: 'Inter', sans-serif;">
          <div style="display: flex; align-items: center; margin-bottom: 8px;">
            ${card.icon ? `<span style="font-size: 20px; margin-right: 8px;">${card.icon}</span>` : ''}
            <span style="font-weight: 800; font-size: 17px; color: #0F172A;">${card.title}</span>
          </div>
          <p style="font-size: 15px; color: #475569; margin: 0; line-height: 1.6;">${card.content}</p>
        </div>
      `).join('')
      return {
        ...baseElement,
        type: 'text',
        content: `<div style="width: 100%;">${cardsHtml}</div>`,
        defaultFontName: whiteTheme.fontName,
        defaultColor: whiteTheme.fontColor,
      }

    case 'CodeSnippet': {
      // 代码块带 Mac 终端风格及高亮
      const lines = block.code.split('\n')
      const codeHtml = lines.map((line, idx) => {
        const highlight = block.highlights.find(h => h.line === idx + 1)
        const bgColor = highlight ? 'rgba(91, 192, 190, 0.12)' : 'transparent'
        const borderLeft = highlight ? '3px solid #5BC0BE' : 'none'
        const noteHtml = highlight ? `<span style="color: #5BC0BE; font-size: 12px; margin-left: 16px; opacity: 0.85;">// ${highlight.note}</span>` : ''
        return `<div style="background: ${bgColor}; border-left: ${borderLeft}; padding: 2px 12px 2px 24px; font-family: 'Fira Code', monospace; line-height: 1.6; white-space: pre-wrap;">${escapeHtml(line)}${noteHtml}</div>`
      }).join('')

      const highlightsList = block.highlights.map(h => `
        <div style="display: flex; align-items: center; gap: 12px; padding: 6px 12px; background: rgba(255, 255, 255, 0.02); border-radius: 6px; border-left: 3px solid #5BC0BE; margin-bottom: 8px;">
          <span style="font-size: 11px; font-weight: 700; color: #5BC0BE; background: rgba(91, 192, 190, 0.15); padding: 2px 6px; border-radius: 4px; font-family: 'Fira Code', monospace;">Line ${h.line}</span>
          <span style="color: #A5A9B4; font-size: 13px; line-height: 1.4;">${h.note}</span>
        </div>
      `).join('')

      return {
        ...baseElement,
        type: 'text',
        content: `
          <div style="background: #0B132B; border-radius: 14px; overflow: hidden; box-shadow: 0 20px 40px rgba(0, 0, 0, 0.25); border: 1px solid rgba(255, 255, 255, 0.05); font-family: 'Fira Code', monospace; width: 100%;">
            <div style="display: flex; align-items: center; justify-content: space-between; padding: 12px 18px; background: #1C2541;">
              <div style="display: flex; gap: 8px;">
                <span style="width: 10px; height: 10px; border-radius: 50%; display: inline-block; background: #FF5F56;"></span>
                <span style="width: 10px; height: 10px; border-radius: 50%; display: inline-block; background: #FFBD2E;"></span>
                <span style="width: 10px; height: 10px; border-radius: 50%; display: inline-block; background: #27C93F;"></span>
              </div>
              <span style="font-size: 11px; font-weight: 800; color: #5BC0BE; letter-spacing: 0.1em; text-transform: uppercase; background: rgba(91, 192, 190, 0.1); padding: 2px 8px; border-radius: 4px;">${block.language}</span>
            </div>
            <div style="display: flex; padding: 16px 0;">
              <div style="flex-grow: 1; color: #E0E1DD; font-size: 13px;">${codeHtml}</div>
            </div>
            ${block.highlights.length > 0 ? `<div style="padding: 16px; background: #090E20; border-top: 1px solid rgba(255, 255, 255, 0.05);">${highlightsList}</div>` : ''}
          </div>
        `,
        defaultFontName: 'Fira Code',
        defaultColor: '#E2E8F0',
      }
    }

    case 'Diagram':
      // 链表/树/图的可视化
      return {
        ...baseElement,
        type: 'text',
        content: generateDiagramHtml(block),
        defaultFontName: whiteTheme.fontName,
        defaultColor: whiteTheme.fontColor,
      }

    case 'FlowChart':
      // 流程图可视化
      return {
        ...baseElement,
        type: 'text',
        content: generateFlowChartHtml(block),
        defaultFontName: whiteTheme.fontName,
        defaultColor: whiteTheme.fontColor,
      }

    case 'Table': {
      const headerHtml = `<tr>${block.columns.map(col => `<th style="background: rgba(37, 99, 235, 0.04); border-bottom: 2px solid rgba(37, 99, 235, 0.08); color: #2563EB; padding: 16px 20px; text-align: left; font-weight: 800; font-size: 15px; letter-spacing: 0.05em;">${col}</th>`).join('')}</tr>`
      const rowsHtml = block.rows.map((row, idx) => {
        const bg = idx % 2 === 1 ? 'rgba(148, 163, 184, 0.02)' : '#FFFFFF'
        return `<tr style="background: ${bg};">${row.map(cell => `<td style="padding: 16px 20px; border-bottom: 1px solid rgba(37, 99, 235, 0.08); color: #475569; font-size: 15px; line-height: 1.5;">${cell}</td>`).join('')}</tr>`
      }).join('')
      return {
        ...baseElement,
        type: 'text',
        content: `
          <div style="background: #FFFFFF; border-radius: 14px; overflow: hidden; border: 1px solid rgba(37, 99, 235, 0.08); box-shadow: 0 10px 30px rgba(15, 23, 42, 0.04); width: 100%;">
            <table style="width: 100%; border-collapse: collapse;">${headerHtml}${rowsHtml}</table>
          </div>
        `,
        defaultFontName: whiteTheme.fontName,
        defaultColor: whiteTheme.fontColor,
      }
    }

    case 'Callout': {
      const intentColors = {
        info: { bg: '#eff6ff', icon: '💡', text: '#1d4ed8' },
        warning: { bg: '#fff7ed', icon: '⚠️', text: '#c2410c' },
        success: { bg: '#ecfdf5', icon: '✓', text: '#047857' },
        danger: { bg: '#fef2f2', icon: '✗', text: '#b91c1c' },
      }
      const style = intentColors[block.intent] || intentColors.info
      return {
        ...baseElement,
        type: 'text',
        content: `
          <div style="background: ${style.bg}; padding: 24px; border-radius: 14px; border-left: 6px solid ${style.text}; border-top: 1px solid rgba(37, 99, 235, 0.08); border-right: 1px solid rgba(37, 99, 235, 0.08); border-bottom: 1px solid rgba(37, 99, 235, 0.08); display: flex; align-items: center; gap: 16px; font-family: 'Inter', sans-serif;">
            <div style="width: 44px; height: 44px; border-radius: 50%; background: #FFFFFF; display: flex; align-items: center; justify-content: center; box-shadow: 0 4px 10px rgba(0, 0, 0, 0.05); flex-shrink: 0;">
              <span style="font-size: 22px;">${style.icon} ${block.icon}</span>
            </div>
            <p style="font-size: 17px; color: ${style.text}; margin: 0; line-height: 1.6; align-self: center;">${block.content}</p>
          </div>
        `,
        defaultFontName: whiteTheme.fontName,
        defaultColor: whiteTheme.fontColor,
      }
    }

    case 'Formula':
      return {
        ...baseElement,
        type: 'text',
        content: `
          <div style="background: linear-gradient(180deg, #FFFFFF 0%, rgba(37, 99, 235, 0.01) 100%); border-top: 4px solid #2563EB; border-left: 1px solid rgba(37, 99, 235, 0.08); border-right: 1px solid rgba(37, 99, 235, 0.08); border-bottom: 1px solid rgba(37, 99, 235, 0.08); padding: 32px 24px; border-radius: 14px; box-shadow: 0 10px 30px rgba(15, 23, 42, 0.04); text-align: center; position: relative;">
            <div style="position: absolute; top: 8px; left: 50%; transform: translateX(-50%); width: 40px; height: 6px; background: rgba(37, 99, 235, 0.08); border-radius: 8px;"></div>
            <p style="font-size: 26px; color: #0F172A; font-family: 'Times New Roman', Times, serif; font-style: italic; margin: 0; display: inline-block; letter-spacing: 0.05em;">${block.formula}</p>
          </div>
        `,
        defaultFontName: 'Times New Roman',
        defaultColor: whiteTheme.fontColor,
      }

    default:
      return {
        ...baseElement,
        type: 'text',
        content: `<p style="color: #94A3B8;">未支持的Block类型: ${(block as any).type}</p>`,
        defaultFontName: whiteTheme.fontName,
        defaultColor: whiteTheme.fontColor,
      }
  }
}

/**
 * HTML转义
 */
function escapeHtml(text: string): string {
  return text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;')
}

/**
 * 生成Diagram的HTML可视化
 * 支持链表、树、图等数据结构的优质 SVG 链条
 */
function generateDiagramHtml(block: DiagramBlock): string {
  const isHorizontal = block.direction === 'LR' || block.direction === 'RL'

  const nodesHtml = block.nodes.map((node, idx) => {
    const isLast = idx === block.nodes.length - 1
    const arrow = isLast ? '' : `
      <div style="display: flex; align-items: center; gap: 4px; ${!isHorizontal ? 'flex-direction: column;' : ''}">
        <div style="${isHorizontal ? 'width: 32px; height: 2px;' : 'width: 2px; height: 32px;'} background: #2563EB; opacity: 0.5;"></div>
        <span style="font-size: 20px; font-weight: 800; color: #2563EB; ${!isHorizontal ? 'transform: rotate(90deg);' : ''}">→</span>
      </div>
    `

    return `
      <div style="display: flex; align-items: center; ${!isHorizontal ? 'flex-direction: column;' : ''}">
        <div style="min-width: 90px; height: 48px; padding: 0 18px; border-radius: 999px; background: linear-gradient(135deg, #3B82F6 0%, #2563EB 100%); border: 2px solid rgba(255, 255, 255, 0.25); box-shadow: 0 8px 16px rgba(37, 99, 235, 0.2); display: flex; align-items: center; justify-content: center;">
          <span style="color: #FFFFFF; font-weight: 800; font-size: 16px; letter-spacing: 0.05em; white-space: nowrap;">${node.label}</span>
        </div>
        ${arrow}
      </div>
    `
  }).join('')

  const edgesListHtml = block.edges && block.edges.some(e => e.label) ? `
    <div style="border-top: 1px dashed rgba(37, 99, 235, 0.08); padding-top: 16px; margin-top: 16px;">
      <div style="font-weight: 800; font-size: 14px; color: #0F172A; margin-bottom: 12px;">节点指向关系 (Edges)</div>
      <div style="display: flex; flex-wrap: wrap; gap: 10px;">
        ${block.edges.map(edge => `
          <div style="padding: 6px 12px; border-radius: 999px; background: rgba(148, 163, 184, 0.05); border: 1px solid rgba(37, 99, 235, 0.08); display: inline-flex; align-items: center; gap: 8px; font-size: 13px;">
            <span style="font-weight: 800; color: #2563EB;">${edge.source}</span>
            <span style="font-family: monospace; color: #475569;">─${edge.label || '指向'}─></span>
            <span style="font-weight: 800; color: #2563EB;">${edge.target}</span>
          </div>
        `).join('')}
      </div>
    </div>
  ` : ''

  return `
    <div style="background: #FFFFFF; border-radius: 18px; border: 1px solid rgba(37, 99, 235, 0.08); box-shadow: 0 10px 30px rgba(15, 23, 42, 0.04); padding: 24px; font-family: 'Inter', sans-serif; width: 100%;">
      <p style="margin: 0 0 16px 0; font-size: 13px; font-weight: 800; color: #475569; text-transform: uppercase; letter-spacing: 0.08em;">结构图示 / ${isHorizontal ? '水平视图' : '垂直视图'}</p>
      <div style="background: #F1F5F9; border-radius: 14px; padding: 32px 20px; display: flex; align-items: center; justify-content: center; border: 1px dashed rgba(37, 99, 235, 0.08);">
        <div style="display: flex; align-items: center; justify-content: center; gap: 12px; flex-wrap: wrap; ${!isHorizontal ? 'flex-direction: column;' : ''}">
          ${nodesHtml}
        </div>
      </div>
      ${edgesListHtml}
    </div>
  `
}

/**
 * 生成FlowChart的HTML可视化
 * 支持算法流程、循环、递归等，样式与 Vue FlowChart 高度同步
 */
function generateFlowChartHtml(block: FlowChartBlock): string {
  const stepsHtml = block.steps.map((step, idx) => {
    const isLast = idx === block.steps.length - 1
    const connector = isLast ? '' : `
      <div style="width: 2px; height: 16px; background-image: linear-gradient(to bottom, rgba(37, 99, 235, 0.08) 50%, transparent 50%); background-size: 2px 8px; background-repeat: repeat-y; margin-left: 20px;"></div>
    `

    const stateHtml = step.state_before || step.state_after ? `
      <div style="display: flex; align-items: center; gap: 6px; padding: 4px 10px; border-radius: 999px; background: #F1F5F9; border: 1px solid rgba(37, 99, 235, 0.08); font-size: 11px; font-family: monospace;">
        <span style="color: #475569;">${step.state_before || '无'}</span>
        <span style="color: #2563EB; font-weight: 800;">→</span>
        <span style="color: #059669; font-weight: 700;">${step.state_after || '无'}</span>
      </div>
    ` : ''

    return `
      <div style="display: flex; flex-direction: column;">
        <div style="display: flex; gap: 20px; align-items: stretch; width: 100%;">
          <div style="flex-shrink: 0; width: 40px; height: 40px; border-radius: 50%; background: #F1F5F9; border: 2px solid rgba(37, 99, 235, 0.08); display: flex; align-items: center; justify-content: center;">
            <span style="font-family: monospace; font-weight: 800; font-size: 15px; color: #475569;">0${idx + 1}</span>
          </div>
          <div style="flex-grow: 1; background: #FFFFFF; border: 1px solid rgba(37, 99, 235, 0.08); border-radius: 14px; box-shadow: 0 10px 30px rgba(15, 23, 42, 0.04); padding: 18px 24px; font-family: 'Inter', sans-serif;">
            <div style="display: flex; align-items: center; justify-content: space-between; gap: 16px; margin-bottom: 8px;">
              <span style="font-weight: 800; font-size: 17px; color: #0F172A;">${step.title}</span>
              ${stateHtml}
            </div>
            <p style="margin: 0; font-size: 15px; color: #475569; line-height: 1.5;">${step.description}</p>
          </div>
        </div>
        ${connector}
      </div>
    `
  }).join('')

  return `
    <div style="width: 100%; display: flex; flex-direction: column; gap: 4px;">
      ${stepsHtml}
    </div>
  `
}

/**
 * 转换PptSlide为PPTist Slide
 */
export function convertSlide(slide: PptSlide, _theme: string): PPTSlide {
  const elements: PPTElement[] = []

  // 转换所有槽位的Block
  for (const [slotName, blocks] of Object.entries(slide.slots)) {
    blocks.forEach((block, index) => {
      const position = getSlotPosition(slide.layout, slotName, index)
      const element = convertBlockToElement(block, position)
      elements.push(element)
    })
  }

  return {
    id: slide.id,
    elements,
    background: { type: 'solid', color: whiteTheme.backgroundColor },
    turningMode: 'fade',
  }
}

/**
 * 转换完整的PptDocument为PPTist Slides
 */
export function convertToPptistSlides(doc: PPTDocument): PPTSlide[] {
  return doc.slides.map(slide => convertSlide(slide, doc.theme_id))
}