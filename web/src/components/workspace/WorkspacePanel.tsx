import { useState } from "react";
import { FolderOpen, RefreshCw, X } from "lucide-react";
import { toast } from "sonner";

import { FileCard } from "@/components/files/FileCard";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Skeleton } from "@/components/ui/skeleton";
import {
  classifyFile,
  downloadAuthenticatedFile,
  previewModeOf,
  type FileCategory,
} from "@/lib/files";
import { cn } from "@/lib/utils";
import type { WorkspaceFile } from "@/types/api";

interface WorkspacePanelProps {
  hasConversation: boolean;
  files: WorkspaceFile[];
  loading: boolean;
  error: string | null;
  newNames: Set<string>;
  onRefresh: () => void;
  onPreview: (file: WorkspaceFile) => void;
  onCloseMobile?: () => void;
}

const FILTER_OPTIONS: { key: "all" | FileCategory; label: string }[] = [
  { key: "all", label: "全部" },
  { key: "document", label: "文档" },
  { key: "slides", label: "课件" },
  { key: "diagram", label: "图解" },
  { key: "video", label: "视频" },
];

function formatModified(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "";
  return d.toLocaleString("zh-CN", {
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function WorkspacePanel({
  hasConversation,
  files,
  loading,
  error,
  newNames,
  onRefresh,
  onPreview,
  onCloseMobile,
}: WorkspacePanelProps) {
  const [filter, setFilter] = useState<"all" | FileCategory>("all");
  const [downloading, setDownloading] = useState<string | null>(null);

  const visibleFiles =
    filter === "all" ? files : files.filter((f) => classifyFile(f.name) === filter);

  const handleDownload = async (file: WorkspaceFile) => {
    setDownloading(file.name);
    try {
      await downloadAuthenticatedFile(file.download_url, file.name);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "下载文件失败");
    } finally {
      setDownloading(null);
    }
  };

  return (
    <aside className="flex h-full w-full flex-col bg-sidebar text-foreground">
      <div className="flex h-12 shrink-0 items-center justify-between border-b border-border/70 px-4">
        <div className="flex items-center gap-2">
          <FolderOpen className="size-4 text-muted-foreground" aria-hidden="true" />
          <h2 className="text-[13px] font-semibold">工作区产物</h2>
          {files.length > 0 && (
            <span className="rounded-md bg-muted px-1.5 py-0.5 font-mono text-[10px] tabular-nums text-muted-foreground">
              {files.length}
            </span>
          )}
        </div>

        <div className="flex items-center gap-1">
          <Button
            type="button"
            size="icon"
            variant="ghost"
            disabled={!hasConversation || loading}
            aria-label="刷新工作区文件"
            onClick={onRefresh}
            className="size-7 text-muted-foreground hover:text-foreground"
          >
            <RefreshCw className={cn("size-3.5", loading && "animate-spin")} aria-hidden="true" />
          </Button>
          {onCloseMobile && (
            <Button
              type="button"
              size="icon"
              variant="ghost"
              aria-label="关闭工作区产物面板"
              onClick={onCloseMobile}
              className="size-7 text-muted-foreground hover:text-foreground"
            >
              <X className="size-4" aria-hidden="true" />
            </Button>
          )}
        </div>
      </div>

      <div
        role="tablist"
        aria-label="产物分类筛选"
        className="flex shrink-0 gap-1 overflow-x-auto border-b border-border/70 px-3 py-2"
      >
        {FILTER_OPTIONS.map((opt) => (
          <button
            key={opt.key}
            type="button"
            role="tab"
            aria-selected={filter === opt.key}
            onClick={() => setFilter(opt.key)}
            className={cn(
              "shrink-0 rounded-lg px-2.5 py-1 text-xs transition-colors",
              filter === opt.key
                ? "bg-primary font-medium text-primary-foreground"
                : "text-muted-foreground hover:bg-muted hover:text-foreground",
            )}
          >
            {opt.label}
          </button>
        ))}
      </div>

      <ScrollArea className="min-h-0 flex-1">
        <div className="p-3">
          {!hasConversation ? (
            <div className="rounded-2xl border border-dashed border-border px-4 py-10 text-center text-xs leading-relaxed text-muted-foreground">
              开始对话后，Agent 在 <code className="font-mono text-foreground">/workspace</code> 下生成的文档、课件、图解和视频会同步到这里。
            </div>
          ) : loading && files.length === 0 ? (
            <div className="space-y-2">
              <Skeleton className="h-18 w-full rounded-2xl" />
              <Skeleton className="h-18 w-full rounded-2xl" />
            </div>
          ) : error ? (
            <div className="rounded-2xl border border-destructive/40 bg-destructive-subtle p-3 text-xs text-destructive">
              {error}
            </div>
          ) : visibleFiles.length === 0 ? (
            <div className="rounded-2xl border border-dashed border-border px-4 py-10 text-center text-xs leading-relaxed text-muted-foreground">
              {files.length === 0
                ? "当前工作区暂无产物。你可以让 Mentorly 生成复习笔记、PPT 课件或讲解视频。"
                : "当前分类下暂无匹配文件。"}
            </div>
          ) : (
            <ul className="space-y-2">
              {visibleFiles.map((file) => {
                const canPreview = previewModeOf(file.name) !== "none";
                return (
                  <li key={file.name}>
                    <FileCard
                      filename={file.name}
                      size={file.size}
                      variant="workspace"
                      isNew={newNames.has(file.name)}
                      meta={formatModified(file.modified_at)}
                      busy={downloading === file.name}
                      onPrimaryAction={() =>
                        canPreview ? onPreview(file) : void handleDownload(file)
                      }
                      onPreview={canPreview ? () => onPreview(file) : undefined}
                      onDownload={() => void handleDownload(file)}
                    />
                  </li>
                );
              })}
            </ul>
          )}
        </div>
      </ScrollArea>
    </aside>
  );
}
