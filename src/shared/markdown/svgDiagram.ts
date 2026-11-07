// SVG 图解渲染器：将 markdown 中的 ```svg 代码块解析并安全替换为交互式矢量图解卡片
//
// 专为计算机专业架构图、协议报文、内存排布与数据流图解设计，
// 提供原生 SVG 渲染、安全防注入（XSS 过滤）、卡片包装、代码复制与下载功能。

let renderSeq = 0

/**
 * 清洗与安全过滤 SVG DOM，防止恶意脚本或事件注入
 */
function sanitizeSvgElement(svg: SVGSVGElement): boolean {
  // 1. 移除所有 <script> 标签
  const scripts = svg.querySelectorAll('script')
  scripts.forEach((s) => s.remove())

  // 2. 遍历所有元素，清除 on* 属性以及 javascript: 协议
  const allElements = svg.querySelectorAll('*')
  allElements.forEach((el) => {
    // 移除 on 开头的事件属性 (如 onclick, onload)
    const attrs = Array.from(el.attributes)
    for (const attr of attrs) {
      if (attr.name.toLowerCase().startsWith('on')) {
        el.removeAttribute(attr.name)
      } else if (
        (attr.name === 'href' || attr.name === 'xlink:href') &&
        attr.value.trim().toLowerCase().startsWith('javascript:')
      ) {
        el.removeAttribute(attr.name)
      }
    }
  })

  // 3. 确保自适应属性
  if (!svg.getAttribute('viewBox')) {
    const width = parseFloat(svg.getAttribute('width') || '0')
    const height = parseFloat(svg.getAttribute('height') || '0')
    if (width > 0 && height > 0) {
      svg.setAttribute('viewBox', `0 0 ${width} ${height}`)
    }
  }

  svg.setAttribute('width', '100%')
  svg.style.maxWidth = '100%'
  svg.style.height = 'auto'
  svg.style.display = 'block'

  return true
}

/**
 * 收集待渲染的 svg 代码块
 */
function collectBlocks(root: HTMLElement): HTMLElement[] {
  const blocks = root.querySelectorAll<HTMLElement>(
    'pre > code.language-svg, pre > code[data-language="svg"]',
  )
  return Array.from(blocks)
    .map((code) => code.parentElement)
    .filter((pre): pre is HTMLElement => pre !== null && !pre.dataset.svgDone)
}

/**
 * 渲染单个 SVG 代码块
 */
function renderBlock(pre: HTMLElement): void {
  const code = pre.querySelector('code')
  const rawSource = (code?.textContent || '').trim()
  if (!rawSource) {
    pre.dataset.svgDone = '1'
    return
  }

  // 标记为已处理
  pre.dataset.svgDone = '1'

  // 从代码文本中提取 <svg ...>...</svg>
  const svgMatch = rawSource.match(/<svg[\s\S]*?<\/svg>/i)
  const svgText = svgMatch ? svgMatch[0] : rawSource

  const parser = new DOMParser()
  const doc = parser.parseFromString(svgText, 'image/svg+xml')
  const parserError = doc.querySelector('parsererror')

  if (parserError || !doc.documentElement || doc.documentElement.tagName.toLowerCase() !== 'svg') {
    // 解析失败：保留为常规代码块，附加错误标注
    pre.dataset.svgError = '1'
    pre.title = parserError ? parserError.textContent || 'SVG 语法错误' : '未找到合法的 SVG 根元素'
    return
  }

  const svgElement = doc.documentElement as unknown as SVGSVGElement
  sanitizeSvgElement(svgElement)

  // 构建设计级卡片容器
  const cardId = `svg-diagram-${++renderSeq}`
  const card = document.createElement('div')
  card.className = 'svg-diagram-card'
  card.id = cardId

  // 卡片 Header
  const header = document.createElement('div')
  header.className = 'svg-diagram-header'

  const titleMeta = document.createElement('div')
  titleMeta.className = 'svg-diagram-meta'
  titleMeta.innerHTML = `
    <span class="svg-diagram-badge">
      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <rect width="18" height="18" x="3" y="3" rx="2" ry="2"/>
        <line x1="3" x2="21" y1="9" y2="9"/>
        <line x1="9" x2="9" y1="21" y2="9"/>
      </svg>
      矢量架构图解
    </span>
  `

  const actions = document.createElement('div')
  actions.className = 'svg-diagram-actions'

  // 复制 SVG 源码按钮
  const copyBtn = document.createElement('button')
  copyBtn.type = 'button'
  copyBtn.className = 'svg-diagram-btn'
  copyBtn.title = '复制 SVG 源码'
  copyBtn.innerHTML = `
    <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
      <rect width="14" height="14" x="8" y="8" rx="2" ry="2"/>
      <path d="M4 16c-1.1 0-2-.9-2-2V4c0-1.1.9-2 2-2h10c1.1 0 2 .9 2 2"/>
    </svg>
    <span>复制</span>
  `
  copyBtn.addEventListener('click', async () => {
    try {
      await navigator.clipboard.writeText(rawSource)
      copyBtn.classList.add('copied')
      const span = copyBtn.querySelector('span')
      if (span) span.textContent = '已复制'
      setTimeout(() => {
        copyBtn.classList.remove('copied')
        if (span) span.textContent = '复制'
      }, 1800)
    } catch {
      // 剪贴板失败 fallback
    }
  })

  // 下载 SVG 按钮
  const downloadBtn = document.createElement('button')
  downloadBtn.type = 'button'
  downloadBtn.className = 'svg-diagram-btn'
  downloadBtn.title = '导出为 SVG 文件'
  downloadBtn.innerHTML = `
    <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
      <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
      <polyline points="7 10 12 15 17 10"/>
      <line x1="12" x2="12" y1="15" y2="3"/>
    </svg>
    <span>导出</span>
  `
  downloadBtn.addEventListener('click', () => {
    const blob = new Blob([svgElement.outerHTML], { type: 'image/svg+xml;charset=utf-8' })
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = `diagram-${Date.now()}.svg`
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    URL.revokeObjectURL(url)
  })

  actions.appendChild(copyBtn)
  actions.appendChild(downloadBtn)
  header.appendChild(titleMeta)
  header.appendChild(actions)

  // 卡片主体 Viewport
  const viewport = document.createElement('div')
  viewport.className = 'svg-diagram-viewport'
  viewport.appendChild(svgElement)

  card.appendChild(header)
  card.appendChild(viewport)

  pre.replaceWith(card)
}

/**
 * 扫描并渲染容器内所有 SVG 代码块
 */
export function renderSvgBlocks(root: HTMLElement | null | undefined): void {
  if (!root) return
  const blocks = collectBlocks(root)
  for (const block of blocks) {
    renderBlock(block)
  }
}
