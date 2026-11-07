// Mermaid 渲染：把 markdown 渲染出的 ```mermaid 代码块替换成 SVG 图
// 支持大模型语法容错清洗、SVG 内存缓存、流式安全（不锁死未完成块）、错误友好回退

import mermaid from 'mermaid'

let initialized = false
let renderSeq = 0

/** Mermaid SVG 内存缓存：key = `${theme}:${cleanSource}`, value = svgString */
const svgCache = new Map<string, string>()

/** 初始化 mermaid（幂等），主题跟随页面 */
function ensureInit(theme: 'light' | 'dark'): void {
  if (initialized) return
  initialized = true
  mermaid.initialize({
    startOnLoad: false,
    theme: theme === 'dark' ? 'dark' : 'default',
    securityLevel: 'loose',
    fontFamily: 'inherit',
    flowchart: { curve: 'basis', useMaxWidth: true, htmlLabels: true },
    sequence: { useMaxWidth: true },
  })
}

/** 大模型 Mermaid 语法自动清洗与容错 */
export function cleanMermaidSource(raw: string): string {
  let text = raw.trim()
  // 去除首尾多余的代码栅栏标记（如大模型流式漏出的 ```mermaid 或 ```）
  text = text.replace(/^```(?:mermaid)?\s*/i, '').replace(/\s*```$/, '').trim()

  // 修复常见的大模型未转义括号问题：A[步骤一(开始)] => A["步骤一(开始)"]
  // 避免括号引起 Mermaid 形状语法解析崩溃
  text = text.replace(/([a-zA-Z0-9_\-\.]+)\s*\[([^"\]\n]+?\([^\n"\]]+?\)[^"\]\n]*?)\]/g, '$1["$2"]')

  return text
}

/** 检查源码是否具备 Mermaid 图表的基础声明骨架 */
function isPotentiallyValidMermaid(source: string): boolean {
  if (!source || source.length < 5) return false
  const validStarters = [
    'graph',
    'flowchart',
    'sequencediagram',
    'classdiagram',
    'statediagram',
    'erdiagram',
    'pie',
    'gantt',
    'gitgraph',
    'journey',
    'mindmap',
    'timeline',
    'quadrantchart',
    'sankey',
    'xychart',
  ]
  const firstLine = source.split('\n')[0]?.trim().toLowerCase() || ''
  return validStarters.some((starter) => firstLine.startsWith(starter))
}

/** 清理 Mermaid 在 DOM 中遗留的错误临时元素 */
function cleanupMermaidTempElements(id: string): void {
  try {
    const el = document.getElementById(id)
    if (el) el.remove()
    const dEl = document.getElementById(`d${id}`)
    if (dEl) dEl.remove()
  } catch {
    // 忽略 DOM 清理异常
  }
}

/** 找到容器内所有未渲染完成的 mermaid 代码块 */
function collectBlocks(root: HTMLElement): HTMLElement[] {
  const blocks = root.querySelectorAll<HTMLElement>(
    'pre > code.language-mermaid, pre > code[data-language="mermaid"]',
  )
  return Array.from(blocks)
    .map((code) => code.parentElement)
    .filter((pre): pre is HTMLElement => pre !== null && !pre.dataset.mermaidDone)
}

/** 渲染单个代码块 */
async function renderBlock(
  pre: HTMLElement,
  theme: 'light' | 'dark',
  isStreaming: boolean,
): Promise<void> {
  const code = pre.querySelector('code')
  const rawSource = (code?.textContent || '').trim()
  if (!rawSource) return

  const source = cleanMermaidSource(rawSource)
  if (!source) return

  // 如果处于流式输出中，且语法骨架尚不完整，绝不渲染且不打死锁标记，等待流式继续输出
  if (isStreaming && !isPotentiallyValidMermaid(source)) {
    return
  }

  ensureInit(theme)
  const cacheKey = `${theme}:${source}`

  // 1. 优先使用缓存的 SVG，实现瞬间恢复
  if (svgCache.has(cacheKey)) {
    const svg = svgCache.get(cacheKey)!
    const wrapper = document.createElement('div')
    wrapper.className = 'mermaid-diagram'
    wrapper.innerHTML = svg
    wrapper.dataset.mermaidDone = '1'
    pre.replaceWith(wrapper)
    return
  }

  const id = `mermaid-${++renderSeq}`

  try {
    const { svg } = await mermaid.render(id, source)
    cleanupMermaidTempElements(id)

    // 成功后缓存
    svgCache.set(cacheKey, svg)

    const wrapper = document.createElement('div')
    wrapper.className = 'mermaid-diagram'
    wrapper.innerHTML = svg
    wrapper.dataset.mermaidDone = '1'
    pre.replaceWith(wrapper)
  } catch {
    cleanupMermaidTempElements(id)

    // 关键修复：如果在流式中报错，绝不打 mermaidDone = '1' 死锁标记！
    // 等后续 token 补齐后还有机会成功渲染！
    if (isStreaming) {
      return
    }

    // 非流式（已结束）状态下确实无法解析时，标记为已处理以避免死循环
    pre.dataset.mermaidDone = '1'
    pre.dataset.mermaidError = '1'
  }
}

/**
 * 渲染容器内所有 mermaid 代码块。
 * @param root 根容器
 * @param theme 主题 ('light' | 'dark')
 * @param isStreaming 是否正处于流式生成中
 */
export async function renderMermaidBlocks(
  root: HTMLElement | null | undefined,
  theme: 'light' | 'dark' = 'light',
  isStreaming = false,
): Promise<void> {
  if (!root) return
  const blocks = collectBlocks(root)
  if (blocks.length === 0) return
  await Promise.all(blocks.map((pre) => renderBlock(pre, theme, isStreaming)))
}
