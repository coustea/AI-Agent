import { ApiError, authHeaders, parseErrorResponse } from "@/lib/api";
import type {
  DoneEventData,
  ErrorEventData,
  MessageEventData,
  ToolEventData,
} from "@/types/api";

export interface StreamHandlers {
  onMessage?: (data: MessageEventData) => void;
  onToolStart?: (data: ToolEventData) => void;
  onToolEnd?: (data: ToolEventData) => void;
  onError?: (data: ErrorEventData) => void;
  onDone?: (data: DoneEventData) => void;
}

export interface ParsedSseFrame {
  event: string;
  data: string;
}

/**
 * 解析单段 SSE 文本流（支持跨 chunk 粘包、CRLF 与 : ping 心跳注释行）。
 */
export function extractSseFrames(buffer: string): {
  frames: ParsedSseFrame[];
  remainder: string;
} {
  const normalized = buffer.replace(/\r\n/g, "\n");
  const blocks = normalized.split("\n\n");
  const remainder = blocks.pop() ?? "";
  const frames: ParsedSseFrame[] = [];

  for (const block of blocks) {
    if (!block.trim()) continue;
    let eventName = "message";
    const dataLines: string[] = [];

    for (const rawLine of block.split("\n")) {
      if (rawLine.startsWith(":")) continue; // 心跳注释如 ": ping"
      if (rawLine.startsWith("event:")) {
        eventName = rawLine.slice(6).trim();
      } else if (rawLine.startsWith("data:")) {
        const val = rawLine.slice(5);
        dataLines.push(val.startsWith(" ") ? val.slice(1) : val);
      }
    }

    if (dataLines.length > 0) {
      frames.push({ event: eventName, data: dataLines.join("\n") });
    }
  }

  return { frames, remainder };
}

export function dispatchSseFrame(frame: ParsedSseFrame, handlers: StreamHandlers): void {
  let parsed: unknown;
  try {
    parsed = JSON.parse(frame.data);
  } catch {
    return;
  }

  switch (frame.event) {
    case "message":
      handlers.onMessage?.(parsed as MessageEventData);
      break;
    case "tool_start":
      handlers.onToolStart?.(parsed as ToolEventData);
      break;
    case "tool_end":
      handlers.onToolEnd?.(parsed as ToolEventData);
      break;
    case "error":
      handlers.onError?.(parsed as ErrorEventData);
      break;
    case "done":
      handlers.onDone?.(parsed as DoneEventData);
      break;
  }
}

export async function streamChatMessage(
  conversationId: string,
  payload: { content: string; attachment_ids?: string[] },
  handlers: StreamHandlers,
  signal?: AbortSignal,
): Promise<void> {
  const res = await fetch(
    `/api/v1/conversations/${encodeURIComponent(conversationId)}/messages`,
    {
      method: "POST",
      headers: authHeaders({
        "Content-Type": "application/json",
        Accept: "text/event-stream",
      }),
      body: JSON.stringify(payload),
      signal,
    },
  );

  if (!res.ok) {
    throw await parseErrorResponse(res);
  }
  if (!res.body) {
    throw new ApiError(res.status, 50000, "服务端未返回流式响应体");
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder("utf-8");
  let buffer = "";

  try {
    while (true) {
      const { value, done } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const { frames, remainder } = extractSseFrames(buffer);
      buffer = remainder;
      for (const frame of frames) {
        dispatchSseFrame(frame, handlers);
      }
    }

    buffer += decoder.decode();
    if (buffer.trim()) {
      const { frames } = extractSseFrames(buffer + "\n\n");
      for (const frame of frames) {
        dispatchSseFrame(frame, handlers);
      }
    }
  } finally {
    reader.releaseLock();
  }
}
