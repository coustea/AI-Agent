import { escapeHtml } from './escapeHtml'
import type {
  MarkdownRenderRequest,
  MarkdownRenderResponse,
  MarkdownRenderResult,
  MarkdownTheme,
} from './types'

// Markdown Worker 客户端：管理 Web Worker 生命周期，支持超时降级和自动重建

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

export interface MarkdownWorkerClientOptions {
  createWorker: () => WorkerLike
  timeoutMs: number
}

export class MarkdownWorkerClient {
  private readonly createWorker: () => WorkerLike
  private readonly timeoutMs: number
  private readonly pending = new Map<number, PendingRender>()
  private worker: WorkerLike | undefined
  private nextRequestId = 1
  private disposed = false

  constructor(options: MarkdownWorkerClientOptions) {
    this.createWorker = options.createWorker
    this.timeoutMs = options.timeoutMs
    this.recreateWorker()
  }

  render(markdown: string, theme: MarkdownTheme): Promise<MarkdownRenderResult> {
    if (this.disposed) {
      return Promise.resolve(this.escapedDegradedResult(markdown, 'Markdown renderer disposed'))
    }

    if (!this.worker) {
      this.recreateWorker()
    }

    const worker = this.worker
    if (!worker) {
      return this.degradedResult(markdown, theme, 'Markdown worker unavailable')
    }

    const requestId = this.nextRequestId
    this.nextRequestId += 1

    return new Promise(resolve => {
      const timer = setTimeout(() => {
        if (!this.pending.has(requestId)) {
          return
        }

        this.failWorker('Markdown rendering timed out')
      }, this.timeoutMs)

      this.pending.set(requestId, { markdown, theme, resolve, timer })

      try {
        worker.postMessage({ type: 'render', requestId, markdown, theme })
      } catch (error: unknown) {
        this.failWorker(this.errorMessage(error, 'Markdown worker failed'))
      }
    })
  }

  dispose(): void {
    if (this.disposed) {
      return
    }

    this.disposed = true
    this.resolveAllPending('Markdown renderer disposed')
    this.detachAndTerminateWorker()
  }

  private recreateWorker(): void {
    if (this.disposed) {
      return
    }

    this.detachAndTerminateWorker()

    try {
      const worker = this.createWorker()
      worker.onmessage = event => {
        if (worker !== this.worker) {
          return
        }
        this.handleMessage(event.data)
      }
      worker.onerror = event => {
        if (worker !== this.worker) {
          return
        }
        event.preventDefault()
        this.failWorker(event.message || 'Markdown worker failed')
      }
      this.worker = worker
    } catch {
      this.worker = undefined
    }
  }

  private handleMessage(response: MarkdownRenderResponse): void {
    const pending = this.pending.get(response.requestId)
    if (!pending) {
      return
    }

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
    if (!this.worker) {
      return
    }

    this.worker.onmessage = null
    this.worker.onerror = null
    this.worker.terminate()
    this.worker = undefined
  }

  private async resolvePendingWithFallback(pending: PendingRender, error: string): Promise<void> {
    pending.resolve(await this.degradedResult(pending.markdown, pending.theme, error))
  }

  private async degradedResult(
    markdown: string,
    theme: MarkdownTheme,
    error: string,
  ): Promise<MarkdownRenderResult> {
    try {
      const { renderMarkdownToHtml } = await import('./pipeline')
      return {
        html: await renderMarkdownToHtml(markdown, theme),
        degraded: false,
        error,
      }
    } catch (fallbackError: unknown) {
      return this.escapedDegradedResult(
        markdown,
        `${error}; fallback render failed: ${this.errorMessage(fallbackError, 'unknown error')}`,
      )
    }
  }

  private escapedDegradedResult(markdown: string, error: string): MarkdownRenderResult {
    return {
      html: escapeHtml(markdown),
      degraded: true,
      error,
    }
  }

  private errorMessage(error: unknown, fallback: string): string {
    return error instanceof Error ? error.message : fallback
  }
}

export function createMarkdownWorkerClient(
  options: MarkdownWorkerClientOptions,
): MarkdownWorkerClient {
  return new MarkdownWorkerClient(options)
}

const markdownWorkerClient = createMarkdownWorkerClient({
  createWorker: () => new Worker(
    new URL('./markdown.worker.ts', import.meta.url),
    { type: 'module' },
  ),
  timeoutMs: 2_000,
})

export function renderMarkdown(
  markdown: string,
  theme: MarkdownTheme,
): Promise<MarkdownRenderResult> {
  return markdownWorkerClient.render(markdown, theme)
}
