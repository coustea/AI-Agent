import { useCallback, useEffect, useRef, useState } from "react";
import { toast } from "sonner";

import { api, ApiError } from "@/lib/api";
import { streamChatMessage } from "@/lib/sse";
import type {
  AttachmentBrief,
  ChatMessageItem,
  Conversation,
  Message,
  ToolStep,
} from "@/types/api";

let clientIdSeq = 0;
function nextClientId(prefix: string): string {
  clientIdSeq += 1;
  return `${prefix}-${Date.now()}-${clientIdSeq}`;
}

function toClientMessages(rows: Message[]): ChatMessageItem[] {
  return rows.map((m) => ({
    ...m,
    clientId: `msg-${m.id}`,
  }));
}

const WORKSPACE_MUTATING_TOOLS = new Set(["write_file", "edit_file", "execute", "task"]);

export function useChat() {
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [loadingConversations, setLoadingConversations] = useState(true);
  const [activeId, setActiveId] = useState<string | null>(null);
  const [messages, setMessages] = useState<ChatMessageItem[]>([]);
  const [loadingMessages, setLoadingMessages] = useState(false);
  const [streaming, setStreaming] = useState(false);
  const [workspaceVersion, setWorkspaceVersion] = useState(0);

  const streamAbortRef = useRef<AbortController | null>(null);
  const loadAbortRef = useRef<AbortController | null>(null);
  const activeIdRef = useRef<string | null>(null);
  const conversationsRef = useRef<Conversation[]>([]);
  const messagesRef = useRef<ChatMessageItem[]>([]);

  activeIdRef.current = activeId;
  conversationsRef.current = conversations;
  messagesRef.current = messages;

  const abortStream = useCallback(() => {
    if (!streamAbortRef.current) return;
    streamAbortRef.current.abort();
    streamAbortRef.current = null;
    setStreaming(false);
  }, []);

  const loadMessages = useCallback(async (conversationId: string) => {
    loadAbortRef.current?.abort();
    const ctrl = new AbortController();
    loadAbortRef.current = ctrl;
    setLoadingMessages(true);
    try {
      const rows = (await api.listMessages(conversationId, ctrl.signal)) ?? [];
      if (!ctrl.signal.aborted) {
        setMessages(toClientMessages(rows));
      }
    } catch (err) {
      if ((err as Error).name === "AbortError") return;
      toast.error(err instanceof Error ? err.message : "加载消息失败");
      setMessages([]);
    } finally {
      if (loadAbortRef.current === ctrl) {
        setLoadingMessages(false);
      }
    }
  }, []);

  const activateConversation = useCallback(
    (id: string | null, shouldLoad: boolean) => {
      loadAbortRef.current?.abort();
      activeIdRef.current = id;
      setActiveId(id);
      if (!id || !shouldLoad) {
        setMessages([]);
        setLoadingMessages(false);
        return;
      }
      void loadMessages(id);
    },
    [loadMessages],
  );

  const loadConversations = useCallback(
    async (selectFirstIfEmpty = false) => {
      try {
        const list = (await api.listConversations(50)) ?? [];
        setConversations(list);
        if (selectFirstIfEmpty && !activeIdRef.current && list[0]) {
          activateConversation(list[0].id, true);
        }
      } catch (err) {
        toast.error(err instanceof Error ? err.message : "加载会话列表失败");
      } finally {
        setLoadingConversations(false);
      }
    },
    [activateConversation],
  );

  useEffect(() => {
    void loadConversations(true);
    return () => {
      loadAbortRef.current?.abort();
      streamAbortRef.current?.abort();
    };
  }, [loadConversations]);

  const selectConversation = useCallback(
    (id: string) => {
      abortStream();
      activateConversation(id, true);
    },
    [abortStream, activateConversation],
  );

  const createConversation = useCallback(async (): Promise<Conversation | null> => {
    abortStream();
    try {
      const conv = await api.createConversation();
      setConversations((prev) => [conv, ...prev.filter((c) => c.id !== conv.id)]);
      activateConversation(conv.id, false);
      return conv;
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "创建会话失败");
      return null;
    }
  }, [abortStream, activateConversation]);

  const renameConversation = useCallback(async (id: string, title: string) => {
    const trimmed = title.trim();
    if (!trimmed) return;
    await api.renameConversation(id, trimmed);
    setConversations((prev) =>
      prev.map((c) => (c.id === id ? { ...c, title: trimmed } : c)),
    );
    toast.success("已更新会话标题");
  }, []);

  const deleteConversation = useCallback(
    async (id: string) => {
      try {
        await api.deleteConversation(id);
        const next = conversationsRef.current.filter((c) => c.id !== id);
        setConversations(next);
        if (activeIdRef.current === id) {
          abortStream();
          activateConversation(next[0]?.id ?? null, Boolean(next[0]));
        }
        toast.success("已删除会话");
      } catch (err) {
        if (err instanceof ApiError && err.status === 409) {
          toast.error("该会话正在生成回答，请先停止生成后再删除");
          return;
        }
        toast.error(err instanceof Error ? err.message : "删除会话失败");
      }
    },
    [abortStream, activateConversation],
  );

  const stopGeneration = useCallback(() => {
    if (streamAbortRef.current) {
      streamAbortRef.current.abort();
      streamAbortRef.current = null;
    }
  }, []);

  const sendMessage = useCallback(
    async (content: string, pendingAttachments: AttachmentBrief[] = []): Promise<boolean> => {
      const trimmed = content.trim();
      if (!trimmed || streaming) return false;

      let convId = activeIdRef.current;
      if (!convId) {
        const created = await createConversation();
        if (!created) return false;
        convId = created.id;
      }

      const now = new Date().toISOString();
      const userClientId = nextClientId("user");
      const assistantClientId = nextClientId("assistant");
      const attachmentIds = pendingAttachments.map((a) => a.id);

      const optimisticUser: ChatMessageItem = {
        id: 0,
        clientId: userClientId,
        role: "user",
        content: trimmed,
        status: "completed",
        attachment_ids: attachmentIds.length > 0 ? attachmentIds : undefined,
        attachments: pendingAttachments.length > 0 ? pendingAttachments : undefined,
        created_at: now,
      };

      const optimisticAssistant: ChatMessageItem = {
        id: 0,
        clientId: assistantClientId,
        role: "assistant",
        content: "",
        status: "streaming",
        toolSteps: [],
        created_at: now,
      };

      setMessages((prev) => [...prev, optimisticUser, optimisticAssistant]);
      setStreaming(true);

      const ctrl = new AbortController();
      streamAbortRef.current = ctrl;

      const updateAssistant = (updater: (msg: ChatMessageItem) => ChatMessageItem) => {
        setMessages((prev) =>
          prev.map((m) => (m.clientId === assistantClientId ? updater(m) : m)),
        );
      };

      try {
        await streamChatMessage(
          convId,
          {
            content: trimmed,
            attachment_ids: attachmentIds.length > 0 ? attachmentIds : undefined,
          },
          {
            onMessage(data) {
              updateAssistant((m) => ({
                ...m,
                content: data.reset ? data.text || "" : m.content + (data.text || ""),
              }));
            },
            onToolStart(data) {
              const step: ToolStep = {
                callId: data.call_id || nextClientId("tool"),
                name: data.name,
                args: data.args,
                status: "running",
              };
              updateAssistant((m) => ({
                ...m,
                toolSteps: [...(m.toolSteps ?? []), step],
              }));
            },
            onToolEnd(data) {
              updateAssistant((m) => {
                const steps = [...(m.toolSteps ?? [])];
                const idx = data.call_id
                  ? steps.findIndex((s) => s.callId === data.call_id)
                  : steps.findLastIndex((s) => s.name === data.name && s.status === "running");
                if (idx >= 0) {
                  steps[idx] = {
                    ...steps[idx],
                    result: data.result,
                    elapsedMs: data.elapsed_ms,
                    status: "done",
                  };
                } else {
                  steps.push({
                    callId: data.call_id || nextClientId("tool-end"),
                    name: data.name,
                    result: data.result,
                    elapsedMs: data.elapsed_ms,
                    status: "done",
                  });
                }
                return { ...m, toolSteps: steps };
              });
              if (WORKSPACE_MUTATING_TOOLS.has(data.name)) {
                setWorkspaceVersion((v) => v + 1);
              }
            },
            onError(data) {
              updateAssistant((m) => ({
                ...m,
                errorMessage: data.message,
                retryable: data.retryable,
              }));
            },
            onDone(data) {
              updateAssistant((m) => ({
                ...m,
                id: data.message_id || m.id,
                status: data.status || "completed",
                elapsedMs: data.elapsed_ms,
                toolSteps: (m.toolSteps ?? []).map((s) =>
                  s.status === "running" ? { ...s, status: "done" } : s,
                ),
              }));
            },
          },
          ctrl.signal,
        );

        await loadConversations(false);
        setWorkspaceVersion((v) => v + 1);
        return true;
      } catch (err) {
        if ((err as Error).name === "AbortError") {
          updateAssistant((m) => ({
            ...m,
            status: "cancelled",
            content: m.content || "[本轮生成已停止]",
            toolSteps: (m.toolSteps ?? []).map((s) =>
              s.status === "running" ? { ...s, status: "done" } : s,
            ),
          }));
          return true;
        }

        const errMsg =
          err instanceof ApiError
            ? err.status === 503
              ? "服务端尚未配置模型凭据（503），请先在 .env 中设置 LLM_API_KEY"
              : err.status === 409
                ? "当前会话正在生成回答，请等待本轮完成后再发送"
                : err.message
            : err instanceof Error
              ? err.message
              : "发送消息失败";

        updateAssistant((m) => ({
          ...m,
          status: "failed",
          errorMessage: errMsg,
          retryable: true,
        }));
        toast.error(errMsg);
        return false;
      } finally {
        if (streamAbortRef.current === ctrl) {
          streamAbortRef.current = null;
        }
        setStreaming(false);
      }
    },
    [createConversation, loadConversations, streaming],
  );

  const retryMessage = useCallback(
    async (assistantClientId: string) => {
      if (streaming) return;
      const current = messagesRef.current;
      const idx = current.findIndex((m) => m.clientId === assistantClientId);
      if (idx < 0) return;

      const targetMsg = current[idx];
      const prevUser = current.slice(0, idx).findLast((m) => m.role === "user");
      if (!prevUser) return;

      if (targetMsg.status === "failed") {
        const removeIds = new Set<string>([targetMsg.clientId]);
        if (prevUser.id === 0) removeIds.add(prevUser.clientId);
        setMessages((prev) => prev.filter((m) => !removeIds.has(m.clientId)));
      }

      await sendMessage(prevUser.content, prevUser.attachments ?? []);
    },
    [sendMessage, streaming],
  );

  const activeConversation = conversations.find((c) => c.id === activeId) ?? null;

  return {
    conversations,
    loadingConversations,
    activeId,
    activeConversation,
    messages,
    loadingMessages,
    streaming,
    workspaceVersion,
    selectConversation,
    createConversation,
    renameConversation,
    deleteConversation,
    sendMessage,
    retryMessage,
    stopGeneration,
  };
}
