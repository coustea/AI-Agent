// src/api/sse.ts — 共享 SSE 流解析工具

import { getAuthToken } from '@/shared/auth/token' // 导入 Token 读取函数

// SSE 模块：建立 Event Stream 连接，逐帧解析 token/done/error 事件

/**
 * 将 SSE data 字段的原始文本解析为结构化数据。
 * 优先 JSON.parse，失败则原样返回字符串。
 */
function normalizeSsePayload(payload: string): unknown {
  const trimmed = payload.trim()
  if (!trimmed) return '' // 空白内容返回空字符串
  try {
    return JSON.parse(trimmed) // 尝试 JSON 解析
  } catch {
    return payload // 解析失败返回原始文本
  }
}

/**
 * 将原始 SSE 文本按双换行拆分为独立帧。
 * 返回已完成帧列表和未完成的尾部（下次拼接用）。
 */
function parseSseFrames(raw: string): { frames: string[]; rest: string } {
  const normalized = raw.replace(/\r\n/g, '\n') // 统一换行符
  const parts = normalized.split('\n\n') // 按双换行拆分帧
  const rest = parts.pop() || '' // 最后一段可能不完整，留作缓冲
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
  url: string // SSE 端点 URL
  method?: string // HTTP 方法（默认 GET）
  headers?: Record<string, string> // 额外请求头
  body?: BodyInit // 请求体（POST 时使用）
  signal?: AbortSignal // 中断信号
  onChunk?: (text: string) => void // 文本增量回调（聊天 token 流）
  onEvent?: (eventName: string, data: unknown) => void // 结构化事件回调
  onDone: () => void // 流结束回调
  onError: (err: Error) => void // 流错误回调
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

  const token = getAuthToken() // 获取认证 Token

  fetch(url, { // 发起 fetch 请求
    method,
    headers: {
      ...(token ? { Authorization: `Bearer ${token}` } : {}), // 附加认证头
      ...headers,
    },
    body,
    signal,
  })
    .then(async (response) => {
      if (!response.ok) { // HTTP 错误处理
        const text = await response.text()
        throw new Error(text || `HTTP ${response.status}`)
      }

      const reader = response.body?.getReader() // 获取 ReadableStream 读取器
      if (!reader) throw new Error('ReadableStream not supported')

      const decoder = new TextDecoder() // 文本解码器
      let buffer = '' // 未解析的缓冲区
      let completed = false // 是否已收到 done 事件

      while (true) { // 持续读取流数据
        const { done, value } = await reader.read()
        if (done) break // 流结束

        buffer += decoder.decode(value, { stream: true }) // 追加解码后的文本
        const { frames, rest } = parseSseFrames(buffer) // 拆分完整帧
        buffer = rest // 保留未完成部分

        for (const frame of frames) { // 逐帧处理
          if (!frame.trim()) continue // 跳过空帧

          let eventName = 'message' // 默认事件名
          const dataLines: string[] = [] // data 行收集器

          frame.split('\n').forEach((line) => { // 解析帧内的 SSE 字段
            if (line.startsWith('event:')) { // event: 行 → 事件名
              eventName = line.slice(6).trim() || 'message'
              return
            }
            if (line.startsWith('data:')) { // data: 行 → 数据内容
              dataLines.push(line.slice(5).replace(/^ /, ''))
            }
          })

          const payloadRaw = dataLines.join('\n') // 合并多行 data
          const payload = normalizeSsePayload(payloadRaw) // 解析为结构化数据

          // token 事件 → 聊天流的文本增量
          if (eventName === 'token') {
            if (onChunk) {
              if (typeof payload === 'string') {
                onChunk(payload)
              } else {
                onChunk(JSON.stringify(payload)) // 非字符串时序列化
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
        onDone() // 仍触发完成回调
      }
    })
    .catch((err) => {
      if (err.name === 'AbortError') return // 主动中断不视为错误
      onError(err)
    })
}
