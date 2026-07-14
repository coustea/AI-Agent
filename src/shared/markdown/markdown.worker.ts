/// <reference lib="webworker" />

import { renderMarkdownToHtml } from './markdown'
import type {
  MarkdownRenderRequest,
  MarkdownRenderResponse,
} from './markdown'

const workerScope: DedicatedWorkerGlobalScope = self as DedicatedWorkerGlobalScope

workerScope.onmessage = async (event: MessageEvent<MarkdownRenderRequest>) => {
  const request = event.data
  if (request?.type !== 'render') {
    return
  }

  let response: MarkdownRenderResponse

  try {
    response = {
      type: 'success',
      requestId: request.requestId,
      html: await renderMarkdownToHtml(request.markdown, request.theme),
    }
  } catch (error: unknown) {
    response = {
      type: 'error',
      requestId: request.requestId,
      message: error instanceof Error ? error.message : 'Markdown rendering failed',
    }
  }

  workerScope.postMessage(response)
}

export {}
