// Markdown 渲染类型定义：Worker 通信协议与渲染结果结构

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
