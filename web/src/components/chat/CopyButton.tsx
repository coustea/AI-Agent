import { useState } from "react";
import { Check, Copy } from "lucide-react";

import { cn } from "@/lib/utils";

interface CopyButtonProps {
  text: string;
  label?: string;
  iconOnly?: boolean;
  className?: string;
}

export function CopyButton({
  text,
  label = "复制",
  iconOnly = false,
  className,
}: CopyButtonProps) {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 1500);
    } catch {
      // 忽略剪贴板受限环境
    }
  };

  return (
    <button
      type="button"
      aria-label={label}
      title={copied ? "已复制" : label}
      onClick={(e) => {
        e.stopPropagation();
        void handleCopy();
      }}
      className={cn(
        "inline-flex items-center justify-center rounded-md text-muted-foreground transition-colors hover:bg-muted hover:text-foreground",
        iconOnly ? "size-6" : "h-7 gap-1 px-2 text-xs",
        className,
      )}
    >
      {copied ? (
        <Check className={cn("size-3.5", iconOnly && "text-foreground")} aria-hidden="true" />
      ) : (
        <Copy className="size-3.5" aria-hidden="true" />
      )}
      {!iconOnly && <span>{copied ? "已复制" : label}</span>}
    </button>
  );
}
