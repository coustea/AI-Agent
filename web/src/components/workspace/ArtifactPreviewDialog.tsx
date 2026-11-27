import { useEffect, useState } from "react";
import { AlertCircle, Download, Loader2, X } from "lucide-react";
import { toast } from "sonner";

import { MarkdownContent } from "@/components/chat/MarkdownContent";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogClose,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  codeFenceLangOf,
  downloadAuthenticatedFile,
  fetchAuthenticatedBlob,
  fetchAuthenticatedText,
  formatBytes,
  previewModeOf,
  wrapAsCodeMarkdown,
} from "@/lib/files";
import type { PreviewableFile } from "@/types/api";

interface ArtifactPreviewDialogProps {
  file: PreviewableFile | null;
  onClose: () => void;
}

export function ArtifactPreviewDialog({ file, onClose }: ArtifactPreviewDialogProps) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [objectUrl, setObjectUrl] = useState<string | null>(null);
  const [textContent, setTextContent] = useState<string | null>(null);
  const [mdView, setMdView] = useState<"rendered" | "source">("rendered");
  const [downloading, setDownloading] = useState(false);

  const mode = file ? previewModeOf(file.name) : "none";
  const codeLang = file ? codeFenceLangOf(file.name) : undefined;

  useEffect(() => {
    setError(null);
    setObjectUrl(null);
    setTextContent(null);
    setMdView("rendered");

    if (!file || mode === "none") {
      setLoading(false);
      return;
    }

    const ctrl = new AbortController();
    let createdUrl: string | null = null;
    setLoading(true);

    const load = async () => {
      try {
        if (mode === "markdown" || mode === "text") {
          setTextContent(await fetchAuthenticatedText(file.download_url, ctrl.signal));
        } else {
          const blob = await fetchAuthenticatedBlob(file.download_url, ctrl.signal);
          createdUrl = URL.createObjectURL(blob);
          setObjectUrl(createdUrl);
        }
      } catch (err) {
        if ((err as Error).name === "AbortError") return;
        setError(err instanceof Error ? err.message : "加载预览失败");
      } finally {
        if (!ctrl.signal.aborted) {
          setLoading(false);
        }
      }
    };

    void load();
    return () => {
      ctrl.abort();
      if (createdUrl) URL.revokeObjectURL(createdUrl);
    };
  }, [file, mode]);

  const handleDownload = async () => {
    if (!file) return;
    setDownloading(true);
    try {
      await downloadAuthenticatedFile(file.download_url, file.name);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "下载文件失败");
    } finally {
      setDownloading(false);
    }
  };

  return (
    <Dialog open={Boolean(file)} onOpenChange={(o) => !o && onClose()}>
      <DialogContent
        showCloseButton={false}
        className="flex max-h-[86dvh] w-full max-w-[min(92vw,880px)] flex-col gap-0 overflow-hidden p-0"
      >
        <DialogHeader className="flex shrink-0 flex-row items-center justify-between gap-3 border-b border-border px-5 py-3.5">
          <div className="min-w-0">
            <DialogTitle className="truncate text-sm font-semibold">
              {file?.name ?? ""}
            </DialogTitle>
            {file && (
              <p className="mt-0.5 font-mono text-[11px] tabular-nums text-muted-foreground">
                {file.path ? `${file.path} · ` : ""}
                {formatBytes(file.size)}
              </p>
            )}
          </div>

          <div className="flex shrink-0 items-center gap-2">
            {mode === "markdown" && (
              <Tabs
                value={mdView}
                onValueChange={(v) => setMdView(v as "rendered" | "source")}
              >
                <TabsList className="h-8">
                  <TabsTrigger value="rendered" className="h-6 px-2.5 text-xs">
                    渲染
                  </TabsTrigger>
                  <TabsTrigger value="source" className="h-6 px-2.5 text-xs">
                    源码
                  </TabsTrigger>
                </TabsList>
              </Tabs>
            )}

            <Button
              type="button"
              size="sm"
              variant="outline"
              disabled={downloading}
              onClick={() => void handleDownload()}
              className="h-8 gap-1.5 text-xs"
            >
              {downloading ? (
                <Loader2 className="size-3.5 animate-spin" aria-hidden="true" />
              ) : (
                <Download className="size-3.5" aria-hidden="true" />
              )}
              <span>下载</span>
            </Button>

            <DialogClose
              aria-label="关闭预览"
              className="flex size-8 items-center justify-center rounded-lg border border-transparent text-muted-foreground transition-colors hover:border-border hover:bg-muted hover:text-foreground"
            >
              <X className="size-4" aria-hidden="true" />
            </DialogClose>
          </div>
        </DialogHeader>

        <div className="min-h-[320px] flex-1 overflow-auto bg-background p-5">
          {loading ? (
            <div className="flex h-64 items-center justify-center gap-2 text-xs text-muted-foreground">
              <Loader2 className="size-4 animate-spin" aria-hidden="true" />
              <span>正在加载预览内容…</span>
            </div>
          ) : error ? (
            <div className="flex items-center gap-2 rounded-xl border border-destructive/40 bg-destructive-subtle p-4 text-xs text-destructive">
              <AlertCircle className="size-4 shrink-0" aria-hidden="true" />
              <span>{error}</span>
            </div>
          ) : mode === "image" && objectUrl ? (
            <div className="flex items-center justify-center">
              <img
                src={objectUrl}
                alt={file?.name ?? "产物预览"}
                className="max-h-[70dvh] max-w-full rounded-xl border border-border object-contain"
              />
            </div>
          ) : mode === "video" && objectUrl ? (
            <video
              src={objectUrl}
              controls
              className="mx-auto max-h-[70dvh] w-full rounded-xl border border-border bg-black"
            />
          ) : mode === "pdf" && objectUrl ? (
            <iframe
              src={objectUrl}
              title={file?.name ?? "PDF 预览"}
              className="h-[72dvh] w-full rounded-xl border border-border"
            />
          ) : mode === "markdown" && textContent !== null ? (
            mdView === "rendered" ? (
              <div className="mx-auto max-w-[72ch]">
                <MarkdownContent content={textContent} />
              </div>
            ) : (
              <pre className="overflow-auto rounded-xl border border-border bg-sidebar p-4 font-mono text-xs leading-relaxed whitespace-pre-wrap break-words text-foreground">
                {textContent}
              </pre>
            )
          ) : mode === "text" && textContent !== null ? (
            codeLang ? (
              <MarkdownContent content={wrapAsCodeMarkdown(textContent, codeLang)} />
            ) : (
              <pre className="overflow-auto rounded-xl border border-border bg-sidebar p-4 font-mono text-xs leading-relaxed whitespace-pre-wrap break-words text-foreground">
                {textContent}
              </pre>
            )
          ) : (
            <div className="flex h-48 flex-col items-center justify-center gap-3 text-xs text-muted-foreground">
              <span>该文件格式不支持内联预览，请点击右上角下载后使用本地应用打开。</span>
            </div>
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
}
