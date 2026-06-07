// src/api/sse.ts — 共享 SSE 流解析工具

/**
 * 将 SSE data 字段的原始文本解析为结构化数据。
 * 优先 JSON.parse，失败则原样返回字符串。
 */
function normalizeSsePayload(payload: string): unknown {
  const trimmed = payload.trim()
  if (!trimmed) return ''
  try {
    return JSON.parse(trimmed)
  } catch {
    return payload
  }
}

/**
 * 将原始 SSE 文本按双换行拆分为独立帧。
 * 返回已完成帧列表和未完成的尾部（下次拼接用）。
 */
function parseSseFrames(raw: string): { frames: string[]; rest: string } {
  const normalized = raw.replace(/\r\n/g, '\n')
  const parts = normalized.split('\n\n')
  const rest = parts.pop() || ''
  return { frames: parts, rest }
}

/**
 * SSE 流配置。
 * - onChunk：仅用于 token 事件（聊天流），资源流不使用。
 * - onEvent：所有非 token/done/error 事件。
 * - onDone：流正常结束（收到 done 事件或 ReadableStream 结束）。
 * - onError：流错误（HTTP 错误、SSE error 事件、网络异常）。
 */
export interface SseStreamConfig {
  url: string
  method?: string
  headers?: Record<string, string>
  body?: BodyInit
  signal?: AbortSignal
  onChunk?: (text: string) => void
  onEvent?: (eventName: string, data: unknown) => void
  onDone: () => void
  onError: (err: Error) => void
}

/**
 * 创建 SSE 流连接并解析事件。
 * 统一了 chat.ts 和 resource.ts 中重复的 fetch + ReadableStream + 帧解析逻辑。
 */
export function createSseStream(config: SseStreamConfig): void {
  const {
    url,
    method = 'GET',
    headers = {},
    body,
    signal,
    onChunk,
    onEvent,
    onDone,
    onError,
  } = config

  const token = localStorage.getItem('token')

  fetch(url, {
    method,
    headers: {
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...headers,
    },
    body,
    signal,
  })
    .then(async (response) => {
      if (!response.ok) {
        const text = await response.text()
        throw new Error(text || `HTTP ${response.status}`)
      }

      const reader = response.body?.getReader()
      if (!reader) throw new Error('ReadableStream not supported')

      const decoder = new TextDecoder()
      let buffer = ''
      let completed = false

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })
        const { frames, rest } = parseSseFrames(buffer)
        buffer = rest

        for (const frame of frames) {
          if (!frame.trim()) continue

          let eventName = 'message'
          const dataLines: string[] = []

          frame.split('\n').forEach((line) => {
            if (line.startsWith('event:')) {
              eventName = line.slice(6).trim() || 'message'
              return
            }
            if (line.startsWith('data:')) {
              dataLines.push(line.slice(5).replace(/^ /, ''))
            }
          })

          const payloadRaw = dataLines.join('\n')
          const payload = normalizeSsePayload(payloadRaw)

          // token 事件 → 聊天流的文本增量
          if (eventName === 'token') {
            if (onChunk) {
              if (typeof payload === 'string') {
                onChunk(payload)
              } else {
                onChunk(JSON.stringify(payload))
              }
            }
            continue
          }

          // 其他事件 → 转发给调用方
          onEvent?.(eventName, payload)

          // error 事件 → 抛出异常
          if (eventName === 'error') {
            const msg =
              typeof payload === 'string'
                ? payload
                : (payload as Record<string, unknown>)?.message
                  ? String((payload as Record<string, unknown>).message)
                  : JSON.stringify(payload)
            throw new Error(msg || 'stream error')
          }

          // done 事件 → 正常结束
          if (eventName === 'done') {
            completed = true
            onDone()
            return
          }
        }
      }

      // ReadableStream 结束但没收到 done 事件
      if (!completed) {
        onDone()
      }
    })
    .catch((err) => {
      if (err.name === 'AbortError') return
      onError(err)
    })
}
