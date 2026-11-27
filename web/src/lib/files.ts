import { authHeaders, parseErrorResponse } from "@/lib/api";

export const ALLOWED_ATTACHMENT_EXTS = [".doc", ".docx", ".pdf", ".md"] as const;
const MAX_ATTACHMENT_BYTES = 5 * 1024 * 1024;
export const MAX_ATTACHMENTS_PER_MESSAGE = 3;

export type FileCategory = "document" | "slides" | "diagram" | "video" | "image" | "code" | "other";
export type PreviewMode = "image" | "pdf" | "video" | "markdown" | "text" | "none";

interface FileTypeSpec {
  category: FileCategory;
  preview: PreviewMode;
  label?: string;
  codeLang?: string;
}

const FILE_TYPES: Record<string, FileTypeSpec> = {
  ".doc": { category: "document", preview: "none" },
  ".docx": { category: "document", preview: "none" },
  ".pdf": { category: "document", preview: "pdf" },
  ".md": { category: "document", preview: "markdown", label: "Markdown" },
  ".txt": { category: "document", preview: "text" },
  ".xlsx": { category: "document", preview: "none" },
  ".csv": { category: "document", preview: "text" },
  ".pptx": { category: "slides", preview: "none" },
  ".potx": { category: "slides", preview: "none" },
  ".excalidraw": { category: "diagram", preview: "text", label: "Excalidraw", codeLang: "json" },
  ".svg": { category: "diagram", preview: "image" },
  ".mp4": { category: "video", preview: "video" },
  ".webm": { category: "video", preview: "video" },
  ".png": { category: "image", preview: "image" },
  ".jpg": { category: "image", preview: "image" },
  ".jpeg": { category: "image", preview: "image" },
  ".webp": { category: "image", preview: "image" },
  ".json": { category: "code", preview: "text", codeLang: "json" },
  ".py": { category: "code", preview: "text", codeLang: "python" },
  ".js": { category: "code", preview: "text", codeLang: "javascript" },
  ".ts": { category: "code", preview: "text", codeLang: "typescript" },
  ".tsx": { category: "code", preview: "text", codeLang: "tsx" },
  ".go": { category: "code", preview: "text", codeLang: "go" },
  ".html": { category: "code", preview: "text", codeLang: "html" },
  ".css": { category: "code", preview: "text", codeLang: "css" },
};

export function getExtension(filename: string): string {
  const idx = filename.lastIndexOf(".");
  return idx >= 0 ? filename.slice(idx).toLowerCase() : "";
}

export function fileFormatLabel(filename: string): string {
  const ext = getExtension(filename);
  return FILE_TYPES[ext]?.label ?? (ext.replace(".", "").toUpperCase() || "FILE").slice(0, 6);
}

export function classifyFile(filename: string): FileCategory {
  return FILE_TYPES[getExtension(filename)]?.category ?? "other";
}

export function previewModeOf(filename: string): PreviewMode {
  return FILE_TYPES[getExtension(filename)]?.preview ?? "none";
}

export function codeFenceLangOf(filename: string): string | undefined {
  return FILE_TYPES[getExtension(filename)]?.codeLang;
}

export function wrapAsCodeMarkdown(content: string, lang: string): string {
  const longestRun = Math.max(2, ...(content.match(/`+/g) ?? []).map((s) => s.length));
  const fence = "`".repeat(longestRun + 1);
  return `${fence}${lang}\n${content}\n${fence}`;
}

export function validateAttachmentFile(file: File): string | null {
  const ext = getExtension(file.name);
  if (!ALLOWED_ATTACHMENT_EXTS.includes(ext as (typeof ALLOWED_ATTACHMENT_EXTS)[number])) {
    return `仅支持 ${ALLOWED_ATTACHMENT_EXTS.join(" / ")} 文档格式`;
  }
  if (file.size > MAX_ATTACHMENT_BYTES) {
    return "单个附件不能超过 5 MB";
  }
  return null;
}

export function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
}

export function formatElapsed(ms?: number): string {
  if (ms === undefined || ms < 0) return "";
  if (ms < 1000) return `${ms} ms`;
  return `${(ms / 1000).toFixed(1)} s`;
}

async function fetchAuthenticated(url: string, signal?: AbortSignal): Promise<Response> {
  const res = await fetch(url, { headers: authHeaders(), signal });
  if (!res.ok) {
    throw await parseErrorResponse(res);
  }
  return res;
}

export async function fetchAuthenticatedBlob(url: string, signal?: AbortSignal): Promise<Blob> {
  return (await fetchAuthenticated(url, signal)).blob();
}

export async function fetchAuthenticatedText(url: string, signal?: AbortSignal): Promise<string> {
  return (await fetchAuthenticated(url, signal)).text();
}

export async function downloadAuthenticatedFile(url: string, filename: string): Promise<void> {
  const blob = await fetchAuthenticatedBlob(url);
  const objectUrl = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = objectUrl;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  window.setTimeout(() => URL.revokeObjectURL(objectUrl), 1000);
}
