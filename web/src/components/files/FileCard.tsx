import { AlertTriangle, Download, Eye, Loader2, X } from "lucide-react";

import { FileIcon } from "@/components/files/FileIcon";
import { fileFormatLabel, formatBytes } from "@/lib/files";
import { cn } from "@/lib/utils";

interface FileCardProps {
  filename: string;
  size: number;
  variant: "composer" | "message" | "workspace";
  busy?: boolean;
  isNew?: boolean;
  meta?: string;
  extractError?: string;
  onPrimaryAction?: () => void;
  onPreview?: () => void;
  onDownload?: () => void;
  onRemove?: () => void;
}

/**
 * Gemini 风格统一文件卡片：用于输入框附件、消息附件与工作区产物列表
 */
export function FileCard({
  filename,
  size,
  variant,
  busy = false,
  isNew = false,
  meta,
  extractError,
  onPrimaryAction,
  onPreview,
  onDownload,
  onRemove,
}: FileCardProps) {
  const formatLabel = fileFormatLabel(filename);
  const compact = variant === "composer";
  const isWorkspace = variant === "workspace";

  const content = (
    <div
      className={cn(
        "flex w-full flex-col gap-1.5 text-left",
        isWorkspace ? "px-3.5 py-3" : compact ? "py-2.5 pr-8 pl-3.5" : "py-3 pr-9 pl-4",
      )}
    >
      <div className={cn("flex w-full min-w-0 items-center gap-1.5", isWorkspace && "pr-12")}>
        <span
          title={filename}
          className={cn(
            "truncate font-medium leading-snug text-foreground",
            isWorkspace ? "text-[13.5px]" : compact ? "text-[13px]" : "text-[14px]",
          )}
        >
          {filename}
        </span>
        {isNew && (
          <span className="inline-flex h-4 shrink-0 items-center rounded-md bg-primary px-1.5 text-[10px] font-medium text-primary-foreground">
            新
          </span>
        )}
      </div>

      <div
        className={cn(
          "flex items-center gap-1.5 text-muted-foreground",
          isWorkspace ? "text-[11.5px]" : "text-[12px]",
        )}
      >
        <FileIcon filename={filename} className="size-4 shrink-0" />
        <span className="shrink-0 font-medium">{formatLabel}</span>
        <span aria-hidden="true" className="opacity-50">
          ·
        </span>
        <span
          className={cn(
            "shrink-0 font-mono tabular-nums",
            isWorkspace ? "text-[11px]" : "text-[11.5px]",
          )}
        >
          {formatBytes(size)}
        </span>

        {meta && (
          <>
            <span aria-hidden="true" className="opacity-50">
              ·
            </span>
            <span className="truncate font-mono text-[10.5px] tabular-nums">{meta}</span>
          </>
        )}

        {extractError && (
          <span
            className="ml-auto inline-flex shrink-0 items-center gap-0.5 text-[11px] font-medium text-destructive"
            title={extractError}
          >
            <AlertTriangle className="size-3" aria-hidden="true" />
            <span>异常</span>
          </span>
        )}
      </div>
    </div>
  );

  return (
    <div
      className={cn(
        "group/file relative overflow-hidden rounded-2xl border border-border/55 bg-file-card transition-colors hover:border-foreground/25",
        isWorkspace ? "w-full" : compact ? "w-[216px] max-w-full" : "w-[236px] max-w-full",
      )}
    >
      {onPrimaryAction ? (
        <button
          type="button"
          onClick={onPrimaryAction}
          disabled={busy}
          className="block w-full text-left focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-inset"
        >
          {content}
        </button>
      ) : (
        content
      )}

      {(onPreview || onDownload) && !compact && (
        <div className="absolute top-2.5 right-2.5 flex items-center gap-0.5 opacity-0 transition-opacity group-hover/file:opacity-100 focus-within:opacity-100">
          {onPreview && (
            <button
              type="button"
              aria-label={`预览 ${filename}`}
              title="预览"
              onClick={(e) => {
                e.stopPropagation();
                onPreview();
              }}
              className="flex size-7 items-center justify-center rounded-lg text-muted-foreground transition-colors hover:bg-background/80 hover:text-foreground"
            >
              <Eye className="size-3.5" aria-hidden="true" />
            </button>
          )}
          {onDownload && (
            <button
              type="button"
              disabled={busy}
              aria-label={`下载 ${filename}`}
              title={`下载 ${filename}`}
              onClick={(e) => {
                e.stopPropagation();
                onDownload();
              }}
              className="flex size-7 items-center justify-center rounded-lg text-muted-foreground transition-colors hover:bg-background/80 hover:text-foreground disabled:opacity-40"
            >
              {busy ? (
                <Loader2 className="size-3.5 animate-spin" aria-hidden="true" />
              ) : (
                <Download className="size-3.5" aria-hidden="true" />
              )}
            </button>
          )}
        </div>
      )}

      {compact && onRemove && (
        <button
          type="button"
          aria-label={`移除附件 ${filename}`}
          onClick={onRemove}
          className="absolute top-2 right-2 flex size-5 items-center justify-center rounded-full text-muted-foreground transition-colors hover:bg-background/80 hover:text-foreground"
        >
          <X className="size-3.5" aria-hidden="true" />
        </button>
      )}
    </div>
  );
}
