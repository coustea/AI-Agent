import { useEffect, useRef, useState } from "react";
import { AlertCircle, ArrowDown, Loader2, RotateCcw } from "lucide-react";
import { toast } from "sonner";

import { BrandMark } from "@/components/BrandMark";
import { CopyButton } from "@/components/chat/CopyButton";
import { MarkdownContent } from "@/components/chat/MarkdownContent";
import { ToolExecutionLedger } from "@/components/chat/ToolExecutionLedger";
import { FileCard } from "@/components/files/FileCard";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import {
  downloadAuthenticatedFile,
  formatElapsed,
  previewModeOf,
} from "@/lib/files";
import type { AttachmentBrief, ChatMessageItem, PreviewableFile } from "@/types/api";

interface MessageListProps {
  messages: ChatMessageItem[];
  loading: boolean;
  streaming: boolean;
  onRetry: (assistantClientId: string) => void;
  onPreviewAttachment: (file: PreviewableFile) => void;
}

function MessageAttachmentItem({
  item,
  onPreview,
}: {
  item: AttachmentBrief;
  onPreview: (file: PreviewableFile) => void;
}) {
  const [busy, setBusy] = useState(false);
  const canPreview = previewModeOf(item.filename) !== "none";

  const handleDownload = async () => {
    setBusy(true);
    try {
      await downloadAuthenticatedFile(item.download_url, item.filename);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "下载附件失败");
    } finally {
      setBusy(false);
    }
  };

  const handlePrimary = () => {
    if (canPreview) {
      onPreview({
        name: item.filename,
        size: item.size,
        download_url: item.download_url,
      });
    } else {
      void handleDownload();
    }
  };

  return (
    <FileCard
      filename={item.filename}
      size={item.size}
      variant="message"
      busy={busy}
      onPrimaryAction={handlePrimary}
      onDownload={() => void handleDownload()}
    />
  );
}

export function MessageList({
  messages,
  loading,
  streaming,
  onRetry,
  onPreviewAttachment,
}: MessageListProps) {
  const scrollerRef = useRef<HTMLDivElement>(null);
  const stickToBottomRef = useRef(true);
  const [showScrollBtn, setShowScrollBtn] = useState(false);

  const handleScroll = () => {
    const el = scrollerRef.current;
    if (!el) return;
    const nearBottom = el.scrollHeight - el.scrollTop - el.clientHeight < 80;
    stickToBottomRef.current = nearBottom;
    setShowScrollBtn(!nearBottom);
  };

  useEffect(() => {
    const el = scrollerRef.current;
    if (!el || !stickToBottomRef.current) return;
    el.scrollTop = el.scrollHeight;
  }, [messages, streaming]);

  const scrollToBottom = () => {
    const el = scrollerRef.current;
    if (!el) return;
    stickToBottomRef.current = true;
    setShowScrollBtn(false);
    el.scrollTo({ top: el.scrollHeight, behavior: "smooth" });
  };

  if (loading) {
    return (
      <div className="mx-auto w-full max-w-[760px] space-y-6 px-4 py-8 sm:px-6">
        <Skeleton className="ml-auto h-12 w-2/3 rounded-2xl" />
        <div className="space-y-2.5">
          <Skeleton className="h-4 w-5/6" />
          <Skeleton className="h-4 w-full" />
          <Skeleton className="h-4 w-3/4" />
        </div>
      </div>
    );
  }

  return (
    <div className="relative min-h-0 flex-1">
      <div
        ref={scrollerRef}
        onScroll={handleScroll}
        className="h-full overflow-y-auto px-4 pt-6 pb-8 sm:px-6"
      >
        <div className="mx-auto w-full max-w-[760px] space-y-8">
          {messages.map((msg, idx) => {
            if (msg.role === "user") {
              return (
                <article key={msg.clientId} className="group flex flex-col items-end gap-1.5">
                  {msg.attachments && msg.attachments.length > 0 && (
                    <div className="flex max-w-[90%] flex-wrap justify-end gap-2">
                      {msg.attachments.map((att) => (
                        <MessageAttachmentItem
                          key={att.id}
                          item={att}
                          onPreview={onPreviewAttachment}
                        />
                      ))}
                    </div>
                  )}
                  <div className="max-w-[84%] rounded-2xl border border-border/70 bg-muted/80 px-4 py-2.5 text-[14.5px] leading-relaxed whitespace-pre-wrap break-words text-foreground">
                    {msg.content}
                  </div>
                  <div className="opacity-0 transition-opacity group-hover:opacity-100 focus-within:opacity-100">
                    <CopyButton text={msg.content} label="复制提问" />
                  </div>
                </article>
              );
            }

            const isStreamingMsg = msg.status === "streaming";
            const hasPrevUser = messages.slice(0, idx).some((m) => m.role === "user");
            const isLastMessage = idx === messages.length - 1;

            return (
              <article key={msg.clientId} className="group flex items-start gap-3">
                <div
                  className="mt-0.5 flex size-7 shrink-0 items-center justify-center rounded-lg border border-border bg-sidebar text-foreground"
                  aria-hidden="true"
                >
                  <BrandMark className={isStreamingMsg ? "size-3.5 animate-pulse" : "size-3.5"} />
                </div>

                <div className="min-w-0 flex-1 space-y-2">
                  <div className="flex items-center justify-between gap-2">
                    <span className="text-xs font-semibold text-foreground">Mentorly</span>
                    <div className="flex items-center gap-2 font-mono text-[11px] tabular-nums text-muted-foreground">
                      {msg.elapsedMs !== undefined && msg.elapsedMs > 0 && (
                        <span>{formatElapsed(msg.elapsedMs)}</span>
                      )}
                      {msg.status === "cancelled" && (
                        <span className="rounded-md bg-muted px-1.5 py-0.5 font-sans text-[10px]">
                          已停止
                        </span>
                      )}
                    </div>
                  </div>

                  {msg.toolSteps && msg.toolSteps.length > 0 && (
                    <ToolExecutionLedger steps={msg.toolSteps} streaming={isStreamingMsg} />
                  )}

                  {msg.content ? (
                    <MarkdownContent content={msg.content} streaming={isStreamingMsg} />
                  ) : isStreamingMsg ? (
                    <div className="flex items-center gap-2 py-1.5 text-xs text-muted-foreground">
                      <Loader2 className="size-3.5 animate-spin text-foreground" aria-hidden="true" />
                      <span>正在思考并组织回答…</span>
                    </div>
                  ) : null}

                  {msg.errorMessage && (
                    <div
                      role="alert"
                      className="flex flex-wrap items-center justify-between gap-2 rounded-xl border border-destructive/40 bg-destructive-subtle px-3.5 py-2.5 text-xs text-destructive"
                    >
                      <span className="flex items-center gap-2">
                        <AlertCircle className="size-4 shrink-0" aria-hidden="true" />
                        <span>{msg.errorMessage}</span>
                      </span>
                      {msg.retryable && hasPrevUser && !streaming && (
                        <Button
                          type="button"
                          size="sm"
                          variant="outline"
                          onClick={() => onRetry(msg.clientId)}
                          className="h-7 gap-1 border-destructive/50 bg-background px-2.5 text-xs text-destructive hover:bg-destructive hover:text-destructive-foreground"
                        >
                          <RotateCcw className="size-3" aria-hidden="true" />
                          <span>重试</span>
                        </Button>
                      )}
                    </div>
                  )}

                  {!isStreamingMsg && msg.content && (
                    <div
                      className={
                        isLastMessage
                          ? "flex items-center gap-1 pt-0.5"
                          : "flex items-center gap-1 pt-0.5 opacity-0 transition-opacity group-hover:opacity-100 focus-within:opacity-100"
                      }
                    >
                      <CopyButton text={msg.content} label="复制回答" />
                      {hasPrevUser && !streaming && (
                        <button
                          type="button"
                          onClick={() => onRetry(msg.clientId)}
                          className="inline-flex h-7 items-center gap-1 rounded-md px-2 text-xs text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
                        >
                          <RotateCcw className="size-3" aria-hidden="true" />
                          <span>重新生成</span>
                        </button>
                      )}
                    </div>
                  )}
                </div>
              </article>
            );
          })}
        </div>
      </div>

      {showScrollBtn && (
        <Button
          type="button"
          size="sm"
          variant="outline"
          onClick={scrollToBottom}
          aria-label="滚动到底部"
          className="absolute bottom-3 left-1/2 h-8 -translate-x-1/2 gap-1.5 rounded-full border-border bg-card px-3.5 text-xs shadow-md hover:bg-muted"
        >
          <ArrowDown className="size-3.5" aria-hidden="true" />
          <span>回到底部</span>
        </Button>
      )}
    </div>
  );
}
