import { describe, expect, it, vi } from "vitest";

import { dispatchSseFrame, extractSseFrames } from "@/lib/sse";

describe("SSE frame parser and dispatcher", () => {
  it("handles chunk boundaries, CRLF, and heartbeat comments", () => {
    const chunk1 = ": ping\r\n\r\nevent: message\r\ndata: {\"text\":\"你好\"}\r\n\r\nevent: tool_start\ndata: {\"name\":\"exe";
    const first = extractSseFrames(chunk1);
    expect(first.frames).toHaveLength(1);
    expect(first.frames[0]).toEqual({ event: "message", data: '{"text":"你好"}' });

    const chunk2 = first.remainder + "cute\",\"call_id\":\"c1\"}\n\n";
    const second = extractSseFrames(chunk2);
    expect(second.frames).toHaveLength(1);
    expect(second.frames[0]).toEqual({
      event: "tool_start",
      data: '{"name":"execute","call_id":"c1"}',
    });
    expect(second.remainder).toBe("");
  });

  it("dispatches reset message, tool lifecycle, error, and done events", () => {
    const onMessage = vi.fn();
    const onToolStart = vi.fn();
    const onToolEnd = vi.fn();
    const onError = vi.fn();
    const onDone = vi.fn();

    dispatchSseFrame(
      { event: "message", data: '{"text":"","reset":true}' },
      { onMessage },
    );
    dispatchSseFrame(
      { event: "tool_start", data: '{"name":"skill","call_id":"sk-1"}' },
      { onToolStart },
    );
    dispatchSseFrame(
      { event: "tool_end", data: '{"name":"skill","call_id":"sk-1","result":"ok","elapsed_ms":42}' },
      { onToolEnd },
    );
    dispatchSseFrame(
      { event: "error", data: '{"message":"上游服务暂时不可用，请重试","retryable":true}' },
      { onError },
    );
    dispatchSseFrame(
      { event: "done", data: '{"message_id":9,"status":"completed","elapsed_ms":1280}' },
      { onDone },
    );

    expect(onMessage).toHaveBeenCalledWith({ text: "", reset: true });
    expect(onToolStart).toHaveBeenCalledWith({ name: "skill", call_id: "sk-1" });
    expect(onToolEnd).toHaveBeenCalledWith({
      name: "skill",
      call_id: "sk-1",
      result: "ok",
      elapsed_ms: 42,
    });
    expect(onError).toHaveBeenCalledWith({
      message: "上游服务暂时不可用，请重试",
      retryable: true,
    });
    expect(onDone).toHaveBeenCalledWith({
      message_id: 9,
      status: "completed",
      elapsed_ms: 1280,
    });
  });
});
