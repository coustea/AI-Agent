// Mermaid 渲染：把 markdown 渲染出的 ```mermaid 代码块替换成 SVG 图
//
// 后端不再把图解渲染成 PNG，模型直接输出 mermaid 代码块。
// 这里在 DOM 挂载后扫描，逐块异步渲染，失败时保留源码并标红。

import mermaid from 'mermaid'

let initialized = false
let renderSeq = 0

/** 初始化 mermaid（幂等），主题跟随页面 */
function ensureInit(theme: 'light' | 'dark'): void {
  if (initialized) return
  initialized = true
  mermaid.initialize({
    startOnLoad: false,
    theme: theme === 'dark' ? 'dark' : 'default',
    securityLevel: 'loose',
    fontFamily: 'inherit',
    flowchart: { curve: 'basis', useMaxWidth: true },
    sequence: { useMaxWidth: true },
  })
}

/** 找到容器内所有未渲染的 mermaid 代码块 */
function collectBlocks(root: HTMLElement): HTMLElement[] {
  const blocks = root.querySelectorAll<HTMLElement>(
    'pre > code.language-mermaid, pre > code[data-language="mermaid"]',
  )
  return Array.from(blocks)
    .map((code) => code.parentElement)
    .filter((pre): pre is HTMLElement => pre !== null && !pre.dataset.mermaidDone)
}

/** 渲染单个代码块；失败时保留源码并给出提示 */
async function renderBlock(pre: HTMLElement, theme: 'light' | 'dark'): Promise<void> {
  const code = pre.querySelector('code')
  const source = (code?.textContent || '').trim()
  if (!source) {
    pre.dataset.mermaidDone = '1'
    return
  }

  ensureInit(theme)
  const id = `mermaid-${++renderSeq}`

  try {
    const { svg } = await mermaid.render(id, source)
    const wrapper = document.createElement('div')
    wrapper.className = 'mermaid-diagram'
    wrapper.innerHTML = svg
    pre.replaceWith(wrapper)
  } catch (error) {
    // 渲染失败：保留源码，加错误标记
    pre.dataset.mermaidDone = '1'
    pre.dataset.mermaidError = '1'
    pre.title = error instanceof Error ? error.message : String(error)
  }
}

/**
 * 渲染容器内所有 mermaid 代码块。
 * 幂等：已渲染过的块会被跳过，可安全地在每次 HTML 更新后调用。
 */
export async function renderMermaidBlocks(
  root: HTMLElement | null | undefined,
  theme: 'light' | 'dark' = 'light',
): Promise<void> {
  if (!root) return
  const blocks = collectBlocks(root)
  if (blocks.length === 0) return
  await Promise.all(blocks.map((pre) => renderBlock(pre, theme)))
}
