import { cn } from "@/lib/utils";

interface BrandMarkProps {
  className?: string;
}

/** 极简几何星芒图标，致敬 Claude Code 终端徽记，严格纯黑白单色渲染 */
export function BrandMark({ className }: BrandMarkProps) {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      aria-hidden="true"
      className={cn("size-4 shrink-0", className)}
    >
      <path
        d="M12 2.5V21.5M2.5 12H21.5M5.3 5.3L18.7 18.7M18.7 5.3L5.3 18.7"
        stroke="currentColor"
        strokeWidth="2.1"
        strokeLinecap="round"
      />
    </svg>
  );
}
