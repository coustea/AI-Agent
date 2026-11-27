import { Icon } from "@iconify/react/dist/offline";
import defaultFileIcon from "@iconify-icons/vscode-icons/default-file";
import cssIcon from "@iconify-icons/vscode-icons/file-type-css";
import csvIcon from "@iconify-icons/vscode-icons/file-type-csv";
import excalidrawIcon from "@iconify-icons/vscode-icons/file-type-excalidraw";
import excelIcon from "@iconify-icons/vscode-icons/file-type-excel";
import goIcon from "@iconify-icons/vscode-icons/file-type-go";
import htmlIcon from "@iconify-icons/vscode-icons/file-type-html";
import imageIcon from "@iconify-icons/vscode-icons/file-type-image";
import jsIcon from "@iconify-icons/vscode-icons/file-type-js-official";
import jsonIcon from "@iconify-icons/vscode-icons/file-type-json";
import markdownIcon from "@iconify-icons/vscode-icons/file-type-markdown";
import pdfIcon from "@iconify-icons/vscode-icons/file-type-pdf2";
import powerpointIcon from "@iconify-icons/vscode-icons/file-type-powerpoint";
import pythonIcon from "@iconify-icons/vscode-icons/file-type-python";
import svgIcon from "@iconify-icons/vscode-icons/file-type-svg";
import textIcon from "@iconify-icons/vscode-icons/file-type-text";
import tsIcon from "@iconify-icons/vscode-icons/file-type-typescript-official";
import videoIcon from "@iconify-icons/vscode-icons/file-type-video";
import wordIcon from "@iconify-icons/vscode-icons/file-type-word";

import { getExtension } from "@/lib/files";
import { cn } from "@/lib/utils";

const EXT_ICON_MAP: Record<string, typeof defaultFileIcon> = {
  ".pdf": pdfIcon,
  ".doc": wordIcon,
  ".docx": wordIcon,
  ".md": markdownIcon,
  ".pptx": powerpointIcon,
  ".potx": powerpointIcon,
  ".xlsx": excelIcon,
  ".csv": csvIcon,
  ".excalidraw": excalidrawIcon,
  ".svg": svgIcon,
  ".mp4": videoIcon,
  ".webm": videoIcon,
  ".png": imageIcon,
  ".jpg": imageIcon,
  ".jpeg": imageIcon,
  ".webp": imageIcon,
  ".go": goIcon,
  ".py": pythonIcon,
  ".ts": tsIcon,
  ".tsx": tsIcon,
  ".js": jsIcon,
  ".json": jsonIcon,
  ".html": htmlIcon,
  ".css": cssIcon,
  ".txt": textIcon,
};

export function FileIcon({
  filename,
  className = "size-4 shrink-0",
}: {
  filename: string;
  className?: string;
}) {
  const ext = getExtension(filename);
  const icon = EXT_ICON_MAP[ext] ?? defaultFileIcon;
  return (
    <Icon
      icon={icon}
      className={cn(className, ext === ".md" && "dark:brightness-[1.9]")}
      aria-hidden="true"
    />
  );
}
