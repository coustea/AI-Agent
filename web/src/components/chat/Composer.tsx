import {
  useEffect,
  useRef,
  useState,
  type Dispatch,
  type DragEvent,
  type FormEvent,
  type KeyboardEvent,
  type SetStateAction,
} from "react";
import {
  ArrowUp,
  FolderOpen,
  Loader2,
  Paperclip,
  Square,
} from "lucide-react";
import { toast } from "sonner";

import { FileCard } from "@/components/files/FileCard";
import { api } from "@/lib/api";
import {
  ALLOWED_ATTACHMENT_EXTS,
  MAX_ATTACHMENTS_PER_MESSAGE,
  validateAttachmentFile,
} from "@/lib/files";
import { cn } from "@/lib/utils";
import type { Attachment } from "@/types/api";

interface ComposerProps {
  value: string;
  onChange: (next: string) => void;
  attachments: Attachment[];
  onAttachmentsChange: Dispatch<SetStateAction<Attachment[]>>;
  streaming: boolean;
  centered?: boolean;
  workspaceCount: number;
  onOpenWorkspace: () => void;
  ensureConversationId: () => Promise<string | null>;
  onSend: (content: string, attachments: Attachment[]) => Promise<boolean>;
  onStop: () => void;
}

export function Composer({
  value,
  onChange,
  attachments,
  onAttachmentsChange,
  streaming,
  centered = false,
  workspaceCount,
  onOpenWorkspace,
  ensureConversationId,
  onSend,
  onStop,
}: ComposerProps) {
  const [uploadingCount, setUploadingCount] = useState(0);
  const [dragging, setDragging] = useState(false);

  const fileInputRef = useRef<HTMLInputElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = `${Math.min(el.scrollHeight, centered ? 220 : 200)}px`;
  }, [value, centered]);

  const uploadFiles = async (fileList: FileList | File[]) => {
    const incoming = Array.from(fileList);
    if (incoming.length === 0) return;

    const remaining = MAX_ATTACHMENTS_PER_MESSAGE - attachments.length;
    if (remaining <= 0) {
      toast.error(`单条消息最多附带 ${MAX_ATTACHMENTS_PER_MESSAGE} 个文档`);
      return;
    }

    const batch = incoming.slice(0, remaining);
    if (incoming.length > remaining) {
      toast.warning(`最多还能添加 ${remaining} 个文档，已忽略多余文件`);
    }

    const validFiles: File[] = [];
    for (const f of batch) {
      const err = validateAttachmentFile(f);
      if (err) {
        toast.error(`${f.name}：${err}`);
      } else {
        validFiles.push(f);
      }
    }
    if (validFiles.length === 0) return;

    const convId = await ensureConversationId();
    if (!convId) return;

    setUploadingCount((n) => n + validFiles.length);
    for (const file of validFiles) {
      try {
        const uploaded = await api.uploadAttachment(convId, file);
        onAttachmentsChange((prev) => [...prev, uploaded]);
        if (uploaded.extract_error) {
          toast.warning(`《${uploaded.filename}》文本提取异常，发送后将提示模型检查状态`);
        }
      } catch (err) {
        toast.error(`${file.name} 上传失败：${err instanceof Error ? err.message : "未知错误"}`);
      } finally {
        setUploadingCount((n) => Math.max(0, n - 1));
      }
    }
  };

  const triggerSend = async () => {
    const text = value.trim();
    if (!text || streaming || uploadingCount > 0) return;
    const toSend = attachments;
    onChange("");
    onAttachmentsChange([]);
    const ok = await onSend(text, toSend);
    if (!ok) {
      onChange(text);
      onAttachmentsChange(toSend);
    }
  };

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    void triggerSend();
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    // IME 组合输入期间绝不拦截 Enter，避免中文选词误发
    if (e.nativeEvent.isComposing || e.keyCode === 229) return;
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      void triggerSend();
    }
  };

  const handleDragLeave = (e: DragEvent<HTMLFormElement>) => {
    if (!e.currentTarget.contains(e.relatedTarget as Node | null)) {
      setDragging(false);
    }
  };

  const handleDrop = (e: DragEvent<HTMLFormElement>) => {
    e.preventDefault();
    setDragging(false);
    if (e.dataTransfer.files?.length) {
      void uploadFiles(e.dataTransfer.files);
    }
  };

  const canSend = Boolean(value.trim()) && uploadingCount === 0;

  return (
    <div
      className={cn(
        centered ? "w-full" : "shrink-0 bg-background px-4 pt-2 pb-4 sm:px-6",
      )}
    >
      <form
        onSubmit={handleSubmit}
        onDragOver={(e) => {
          e.preventDefault();
          setDragging(true);
        }}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        className={cn(
          "composer-surface relative mx-auto w-full max-w-[760px] rounded-2xl border bg-elevated transition-colors",
          dragging
            ? "border-foreground bg-sidebar"
            : "border-border focus-within:border-foreground/40",
        )}
      >
        {attachments.length > 0 && (
          <div className="flex flex-wrap gap-2.5 border-b border-border/70 px-3.5 pt-3 pb-3">
            {attachments.map((att) => (
              <FileCard
                key={att.id}
                filename={att.filename}
                size={att.size}
                variant="composer"
                extractError={att.extract_error}
                onRemove={() =>
                  onAttachmentsChange((prev) => prev.filter((a) => a.id !== att.id))
                }
              />
            ))}
          </div>
        )}

        <div className="px-4 pt-3.5 pb-1">
          <label htmlFor="chat-composer" className="sr-only">
            输入学习问题或创作任务
          </label>
          <textarea
            ref={textareaRef}
            id="chat-composer"
            name="content"
            rows={centered ? 3 : 2}
            maxLength={20000}
            value={value}
            onChange={(e) => onChange(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={
              dragging
                ? "释放文件以上传到当前对话（支持 .doc / .docx / .pdf / .md）"
                : "向 Mentorly 提问、粘贴代码，或拖拽学习文档到这里…"
            }
            className="block max-h-[220px] w-full resize-none bg-transparent text-[14.5px] leading-relaxed text-foreground placeholder:text-muted-foreground focus:outline-none"
          />
        </div>

        <div className="flex items-center justify-between gap-2 px-3 pt-1.5 pb-2.5">
          <div className="flex items-center gap-1.5">
            <input
              ref={fileInputRef}
              type="file"
              multiple
              accept={ALLOWED_ATTACHMENT_EXTS.join(",")}
              className="sr-only"
              onChange={(e) => {
                if (e.target.files?.length) {
                  void uploadFiles(e.target.files);
                }
                e.target.value = "";
              }}
            />

            <button
              type="button"
              disabled={uploadingCount > 0 || attachments.length >= MAX_ATTACHMENTS_PER_MESSAGE}
              onClick={() => fileInputRef.current?.click()}
              className="inline-flex h-8 items-center gap-1.5 rounded-lg px-2.5 text-xs text-muted-foreground transition-colors hover:bg-muted hover:text-foreground disabled:pointer-events-none disabled:opacity-45"
            >
              {uploadingCount > 0 ? (
                <Loader2 className="size-3.5 animate-spin" aria-hidden="true" />
              ) : (
                <Paperclip className="size-3.5" aria-hidden="true" />
              )}
              <span>
                {uploadingCount > 0
                  ? `上传中 (${uploadingCount})`
                  : attachments.length > 0
                    ? `文档 ${attachments.length}/${MAX_ATTACHMENTS_PER_MESSAGE}`
                    : "添加文档"}
              </span>
            </button>

            <button
              type="button"
              title="切换工作区产物面板"
              onClick={onOpenWorkspace}
              className="hidden h-8 items-center gap-1.5 rounded-lg px-2.5 font-mono text-[11px] text-muted-foreground transition-colors hover:bg-muted hover:text-foreground sm:inline-flex"
            >
              <FolderOpen className="size-3.5" aria-hidden="true" />
              <span>/workspace</span>
              {workspaceCount > 0 && (
                <span className="tabular-nums text-foreground">({workspaceCount})</span>
              )}
            </button>
          </div>

          <div className="flex items-center gap-2.5">
            {value.length > 200 ? (
              <span className="font-mono text-[11px] tabular-nums text-muted-foreground">
                {value.length} / 20000
              </span>
            ) : (
              <span className="hidden text-[11px] text-muted-foreground sm:inline">
                Enter 发送 · Shift+Enter 换行
              </span>
            )}

            {streaming ? (
              <button
                type="button"
                onClick={onStop}
                aria-label="停止生成"
                className="inline-flex h-8 items-center gap-1.5 rounded-lg border border-foreground bg-background px-3 text-xs font-medium text-foreground transition-colors hover:bg-muted"
              >
                <Square className="size-3 fill-current" aria-hidden="true" />
                <span>停止</span>
              </button>
            ) : (
              <button
                type="submit"
                disabled={!canSend}
                aria-label="发送消息"
                className="inline-flex size-8 items-center justify-center rounded-lg bg-primary text-primary-foreground transition-colors hover:bg-primary/90 disabled:pointer-events-none disabled:opacity-30"
              >
                <ArrowUp className="size-4" aria-hidden="true" />
              </button>
            )}
          </div>
        </div>
      </form>
    </div>
  );
}
