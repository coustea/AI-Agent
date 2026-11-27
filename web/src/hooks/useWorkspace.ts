import { useCallback, useEffect, useRef, useState } from "react";

import { api } from "@/lib/api";
import type { WorkspaceFile } from "@/types/api";

export function useWorkspace(conversationId: string | null, refreshToken = 0) {
  const [files, setFiles] = useState<WorkspaceFile[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [newNames, setNewNames] = useState<Set<string>>(new Set());
  const prevNamesRef = useRef<Set<string>>(new Set());
  const prevConvIdRef = useRef<string | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  const refresh = useCallback(
    async (highlightNew = false) => {
      if (!conversationId) {
        setFiles([]);
        setError(null);
        setNewNames(new Set());
        prevNamesRef.current = new Set();
        return;
      }

      abortRef.current?.abort();
      const ctrl = new AbortController();
      abortRef.current = ctrl;

      setLoading(true);
      setError(null);
      try {
        const rows = (await api.listWorkspaceFiles(conversationId, ctrl.signal)) ?? [];
        if (ctrl.signal.aborted) return;
        if (highlightNew) {
          const added = new Set<string>();
          for (const f of rows) {
            if (!prevNamesRef.current.has(f.name)) added.add(f.name);
          }
          if (added.size > 0) setNewNames(added);
        } else {
          setNewNames(new Set());
        }
        prevNamesRef.current = new Set(rows.map((f) => f.name));
        setFiles(rows);
      } catch (err) {
        if ((err as Error).name === "AbortError") return;
        setError(err instanceof Error ? err.message : "加载工作区文件失败");
      } finally {
        if (abortRef.current === ctrl) {
          setLoading(false);
        }
      }
    },
    [conversationId],
  );

  useEffect(() => {
    const isSameConversation = prevConvIdRef.current === conversationId;
    prevConvIdRef.current = conversationId;
    void refresh(isSameConversation && refreshToken > 0);
    return () => abortRef.current?.abort();
  }, [conversationId, refreshToken, refresh]);

  const clearNewFlag = useCallback((name: string) => {
    setNewNames((prev) => {
      if (!prev.has(name)) return prev;
      const next = new Set(prev);
      next.delete(name);
      return next;
    });
  }, []);

  return { files, loading, error, newNames, refresh, clearNewFlag };
}
