import githubDark from '@shikijs/themes/github-dark'
import githubLight from '@shikijs/themes/github-light'
import rehypeShikiFromHighlighter from '@shikijs/rehype/core'
import type { Element, ElementContent, Root } from 'hast'
import { toString } from 'hast-util-to-string'
import type { Schema } from 'hast-util-sanitize'
import rehypeKatex from 'rehype-katex'
import { defaultSchema } from 'rehype-sanitize'
import rehypeSanitize from 'rehype-sanitize'
import rehypeStringify from 'rehype-stringify'
import remarkGfm from 'remark-gfm'
import remarkMath from 'remark-math'
import remarkParse from 'remark-parse'
import remarkRehype from 'remark-rehype'
import { createHighlighterCore, type HighlighterCore, type LanguageInput } from 'shiki/core'
import { createJavaScriptRegexEngine } from 'shiki/engine/javascript'
import { unified, type Plugin } from 'unified'
import { visit } from 'unist-util-visit'

/** Shared Markdown runtime: worker protocol, rendering pipeline, code decoration, and client fallback. */
export type MarkdownTheme = 'light' | 'dark'

export interface MarkdownRenderRequest {
  type: 'render'
  requestId: number
  markdown: string
  theme: MarkdownTheme
}

export interface MarkdownRenderSuccess {
  type: 'success'
  requestId: number
  html: string
}

export interface MarkdownRenderFailure {
  type: 'error'
  requestId: number
  message: string
}

export type MarkdownRenderResponse = MarkdownRenderSuccess | MarkdownRenderFailure

export interface MarkdownRenderResult {
  html: string
  degraded: boolean
  error?: string
}

export function escapeHtml(value: string): string {
  return value
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;')
}

export const MAX_HIGHLIGHT_CHARS = 50_000
export const MAX_HIGHLIGHT_LINES = 2_000

export const languageLoaders = {
  python: () => import('@shikijs/langs/python').then(module => module.default),
  c: () => import('@shikijs/langs/c').then(module => module.default),
  cpp: () => import('@shikijs/langs/cpp').then(module => module.default),
  java: () => import('@shikijs/langs/java').then(module => module.default),
  javascript: () => import('@shikijs/langs/javascript').then(module => module.default),
  typescript: () => import('@shikijs/langs/typescript').then(module => module.default),
  vue: () => import('@shikijs/langs/vue').then(module => module.default),
  html: () => import('@shikijs/langs/html').then(module => module.default),
  css: () => import('@shikijs/langs/css').then(module => module.default),
  sql: () => import('@shikijs/langs/sql').then(module => module.default),
  bash: () => import('@shikijs/langs/bash').then(module => module.default),
  go: () => import('@shikijs/langs/go').then(module => module.default),
  rust: () => import('@shikijs/langs/rust').then(module => module.default),
  json: () => import('@shikijs/langs/json').then(module => module.default),
  yaml: () => import('@shikijs/langs/yaml').then(module => module.default),
} satisfies Record<string, LanguageInput>

const languageAliases: Record<string, string> = {
  py: 'python', js: 'javascript', jsx: 'javascript', ts: 'typescript', tsx: 'typescript',
  sh: 'bash', shell: 'bash', yml: 'yaml', 'c++': 'cpp', cplusplus: 'cpp', h: 'c', hpp: 'cpp',
}

export function normalizeLanguage(value: string): string {
  const normalized = value.trim().toLowerCase()
  const canonical = languageAliases[normalized] ?? normalized
  return Object.prototype.hasOwnProperty.call(languageLoaders, canonical) ? canonical : 'text'
}

export function shouldHighlight(code: string, language: string): boolean {
  return normalizeLanguage(language) !== 'text'
    && code.length <= MAX_HIGHLIGHT_CHARS
    && code.split('\n').length <= MAX_HIGHLIGHT_LINES
}

export const markdownSanitizeSchema: Schema = {
  ...defaultSchema,
  attributes: {
    ...defaultSchema.attributes,
    code: [...(defaultSchema.attributes?.code ?? []), ['className', /^language-./, 'math-inline', 'math-display']],
    pre: [...(defaultSchema.attributes?.pre ?? []), ['dataLanguage']],
    div: [...(defaultSchema.attributes?.div ?? []), 'className'],
    span: [...(defaultSchema.attributes?.span ?? []), 'className'],
    strong: [...(defaultSchema.attributes?.strong ?? []), 'className'],
  },
}

let codeHighlighter: HighlighterCore | undefined
const languagePromises = new Map<string, Promise<void>>()

function configureCodeBlockHighlighter(value: HighlighterCore): void {
  if (codeHighlighter !== value) {
    codeHighlighter = value
    languagePromises.clear()
  }
}

function loadLanguage(language: string): Promise<void> {
  const existing = languagePromises.get(language)
  if (existing) return existing

  const loader = languageLoaders[language as keyof typeof languageLoaders]
  const promise = loader().then(grammar => codeHighlighter?.loadLanguage(grammar)).then(() => undefined)
  languagePromises.set(language, promise)
  return promise
}

function readLanguage(code: Element): string {
  const classes = code.properties.className
  if (!Array.isArray(classes)) return 'text'
  const languageClass = classes.find(value => typeof value === 'string' && value.startsWith('language-'))
  return typeof languageClass === 'string' ? normalizeLanguage(languageClass.slice('language-'.length)) : 'text'
}

function rehypePrepareCodeBlocks(): (tree: Root) => Promise<void> {
  return async tree => {
    const pending: Promise<void>[] = []
    visit(tree, 'element', node => {
      if (node.tagName !== 'pre') return
      const code = node.children[0]
      if (code?.type !== 'element' || code.tagName !== 'code') return

      const requestedLanguage = readLanguage(code)
      const language = shouldHighlight(toString(code), requestedLanguage) ? requestedLanguage : 'text'
      node.properties.dataLanguage = language
      if (language === 'text') {
        code.properties.className = []
        return
      }
      code.properties.className = [`language-${language}`]
      pending.push(loadLanguage(language))
    })
    await Promise.all(pending)
  }
}

function element(tagName: string, properties: Element['properties'], children: ElementContent[]): Element {
  return { type: 'element', tagName, properties, children }
}

function addCodeLineClass(node: Element): void {
  for (const child of node.children) {
    if (child.type !== 'element') continue
    if (child.tagName === 'span') {
      const classValue = child.properties.className ?? child.properties.class
      const classes = Array.isArray(classValue) ? classValue : typeof classValue === 'string' ? classValue.split(/\s+/) : []
      if (classes.includes('line') && !classes.includes('code-line')) {
        delete child.properties.class
        child.properties.className = [...classes, 'code-line']
      }
    }
    addCodeLineClass(child)
  }
}

function addPlainCodeLines(code: Element): void {
  const value = toString(code)
  const lines = (value.endsWith('\n') ? value.slice(0, -1) : value).split('\n')
  code.children = lines.flatMap((line, index) => {
    const lineElement = element('span', { className: ['line', 'code-line'] }, [{ type: 'text', value: line }])
    return index < lines.length - 1 ? [lineElement, { type: 'text' as const, value: '\n' }] : [lineElement]
  })
}

function codeLineCount(code: Element | undefined): number {
  if (!code) return 0
  const value = toString(code)
  if (!value) return 0
  return (value.endsWith('\n') ? value.slice(0, -1) : value).split('\n').length
}

function rehypeDecorateCodeBlocks(): (tree: Root) => void {
  return tree => {
    visit(tree, 'element', (node, index, parent) => {
      if (node.tagName !== 'pre' || index === undefined || !parent) return
      const language = typeof node.properties.dataLanguage === 'string' ? node.properties.dataLanguage : 'text'
      const code = node.children[0]
      if (language === 'text' && code?.type === 'element' && code.tagName === 'code') {
        code.properties.className = ['language-text']
        addPlainCodeLines(code)
      }
      addCodeLineClass(node)
      const header = element('div', { className: ['code-block-header'] }, [
        element('div', { className: ['code-block-meta'] }, [
          element('span', { className: ['code-block-language'] }, [{ type: 'text', value: language }]),
          element('span', { className: ['code-block-lines'] }, [{ type: 'text', value: `${codeLineCount(code?.type === 'element' ? code : undefined)} 行` }]),
        ]),
        element('div', { className: ['code-block-actions'] }, [
          element('button', {
            type: 'button', className: ['code-block-wrap'], dataCodeAction: 'wrap', ariaPressed: 'false', ariaLabel: '自动换行',
          }, [{ type: 'text', value: '自动换行' }]),
          element('button', {
            type: 'button', className: ['code-block-copy'], dataCodeAction: 'copy', ariaLabel: `复制 ${language} 代码`,
          }, [{ type: 'text', value: '复制代码' }]),
        ]),
      ])
      parent.children[index] = element('div', { className: ['code-block-wrapper'], dataLanguage: language }, [
        header,
        element('div', { className: ['code-block-scroll'] }, [node]),
      ])
      return 'skip'
    })
  }
}

let highlighterPromise: Promise<HighlighterCore> | undefined

function getHighlighter(): Promise<HighlighterCore> {
  highlighterPromise ??= createHighlighterCore({
    themes: [githubLight, githubDark],
    langs: [],
    engine: createJavaScriptRegexEngine(),
  })
  return highlighterPromise
}

function rehypeExternalLinkPolicy(): (tree: Root) => void {
  return tree => {
    visit(tree, 'element', node => {
      if (node.tagName !== 'a' || typeof node.properties.href !== 'string' || !/^https?:\/\//i.test(node.properties.href)) return
      try {
        const url = new URL(node.properties.href)
        if (url.protocol === 'http:' || url.protocol === 'https:') {
          node.properties.target = '_blank'
          node.properties.rel = ['noopener', 'noreferrer']
        }
      } catch {
        // Malformed links are left for the sanitizer to handle.
      }
    })
  }
}

const rehypeSafeMarkdown: Plugin<[], Root> = () => rehypeSanitize(markdownSanitizeSchema)
const rehypeRenderMath: Plugin<[], Root> = () => rehypeKatex({ strict: 'ignore' })

export async function renderMarkdownToHtml(markdown: string, theme: MarkdownTheme): Promise<string> {
  const highlighter = await getHighlighter()
  configureCodeBlockHighlighter(highlighter)
  const processor = unified()
    .use(remarkParse)
    .use(remarkGfm)
    .use(remarkMath)
    .use(remarkRehype)
    .use(rehypeSafeMarkdown)
    .use(rehypeRenderMath)
    .use(rehypePrepareCodeBlocks)
    .use(() => rehypeShikiFromHighlighter(
      highlighter as unknown as Parameters<typeof rehypeShikiFromHighlighter>[0],
      {
        themes: { light: 'github-light', dark: 'github-dark' },
        defaultColor: theme,
        fallbackLanguage: 'text',
        transformers: [{
          name: 'markdown-code-metadata',
          pre(node: Element) {
            node.properties.dataLanguage = this.options.lang
            node.properties.dataTheme = theme
          },
        }],
      },
    ))
    .use(rehypeDecorateCodeBlocks)
    .use(rehypeExternalLinkPolicy)
    .use(rehypeStringify)
  return String(await processor.process(markdown))
}

export interface WorkerLike {
  onmessage: ((event: MessageEvent<MarkdownRenderResponse>) => void) | null
  onerror: ((event: ErrorEvent) => void) | null
  postMessage(message: MarkdownRenderRequest): void
  terminate(): void
}

interface PendingRender {
  markdown: string
  theme: MarkdownTheme
  resolve: (result: MarkdownRenderResult) => void
  timer: ReturnType<typeof setTimeout>
}

export class MarkdownWorkerClient {
  private readonly pending = new Map<number, PendingRender>()
  private readonly options: { createWorker: () => WorkerLike; timeoutMs: number }
  private worker: WorkerLike | undefined
  private nextRequestId = 1
  private disposed = false

  constructor(options: { createWorker: () => WorkerLike; timeoutMs: number }) {
    this.options = options
    this.recreateWorker()
  }

  render(markdown: string, theme: MarkdownTheme): Promise<MarkdownRenderResult> {
    if (this.disposed) return Promise.resolve(this.escapedDegradedResult(markdown, 'Markdown renderer disposed'))
    if (!this.worker) this.recreateWorker()
    const worker = this.worker
    if (!worker) return this.degradedResult(markdown, theme, 'Markdown worker unavailable')

    const requestId = this.nextRequestId++
    return new Promise(resolve => {
      const timer = setTimeout(() => {
        if (this.pending.has(requestId)) this.failWorker('Markdown rendering timed out')
      }, this.options.timeoutMs)
      this.pending.set(requestId, { markdown, theme, resolve, timer })
      try {
        worker.postMessage({ type: 'render', requestId, markdown, theme })
      } catch (error: unknown) {
        this.failWorker(this.errorMessage(error, 'Markdown worker failed'))
      }
    })
  }

  dispose(): void {
    if (this.disposed) return
    this.disposed = true
    this.resolveAllPending('Markdown renderer disposed')
    this.detachAndTerminateWorker()
  }

  private recreateWorker(): void {
    if (this.disposed) return
    this.detachAndTerminateWorker()
    try {
      const worker = this.options.createWorker()
      worker.onmessage = event => {
        if (worker === this.worker) this.handleMessage(event.data)
      }
      worker.onerror = event => {
        if (worker === this.worker) {
          event.preventDefault()
          this.failWorker(event.message || 'Markdown worker failed')
        }
      }
      this.worker = worker
    } catch {
      this.worker = undefined
    }
  }

  private handleMessage(response: MarkdownRenderResponse): void {
    const pending = this.pending.get(response.requestId)
    if (!pending) return
    clearTimeout(pending.timer)
    this.pending.delete(response.requestId)
    if (response.type === 'success') {
      pending.resolve({ html: response.html, degraded: false })
      return
    }
    void this.resolvePendingWithFallback(pending, response.message)
  }

  private failWorker(message: string): void {
    this.resolveAllPending(message)
    this.recreateWorker()
  }

  private resolveAllPending(message: string): void {
    for (const pending of this.pending.values()) {
      clearTimeout(pending.timer)
      void this.resolvePendingWithFallback(pending, message)
    }
    this.pending.clear()
  }

  private detachAndTerminateWorker(): void {
    if (!this.worker) return
    this.worker.onmessage = null
    this.worker.onerror = null
    this.worker.terminate()
    this.worker = undefined
  }

  private async resolvePendingWithFallback(pending: PendingRender, error: string): Promise<void> {
    pending.resolve(await this.degradedResult(pending.markdown, pending.theme, error))
  }

  private async degradedResult(markdown: string, theme: MarkdownTheme, error: string): Promise<MarkdownRenderResult> {
    try {
      return { html: await renderMarkdownToHtml(markdown, theme), degraded: false, error }
    } catch (fallbackError: unknown) {
      return this.escapedDegradedResult(markdown, `${error}; fallback render failed: ${this.errorMessage(fallbackError, 'unknown error')}`)
    }
  }

  private escapedDegradedResult(markdown: string, error: string): MarkdownRenderResult {
    return { html: escapeHtml(markdown), degraded: true, error }
  }

  private errorMessage(error: unknown, fallback: string): string {
    return error instanceof Error ? error.message : fallback
  }
}

const markdownWorkerClient = new MarkdownWorkerClient({
  createWorker: () => new Worker(new URL('./markdown.worker.ts', import.meta.url), { type: 'module' }),
  timeoutMs: 2_000,
})

export function renderMarkdown(markdown: string, theme: MarkdownTheme): Promise<MarkdownRenderResult> {
  return markdownWorkerClient.render(markdown, theme)
}
