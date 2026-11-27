import * as React from "react";

import { cn } from "@/lib/utils";

const VARIANTS = {
  default: "bg-primary text-primary-foreground hover:bg-primary/90",
  outline: "border border-border bg-background text-foreground hover:bg-muted",
  secondary: "bg-secondary text-secondary-foreground hover:bg-secondary/80",
  ghost: "text-foreground hover:bg-muted",
} as const;

const SIZES = {
  default: "h-9 px-4 py-2",
  sm: "h-8 px-3 text-xs",
  icon: "size-9",
} as const;

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: keyof typeof VARIANTS;
  size?: keyof typeof SIZES;
}

export function Button({
  className,
  variant = "default",
  size = "default",
  ...props
}: ButtonProps) {
  return (
    <button
      className={cn(
        "inline-flex shrink-0 items-center justify-center gap-1.5 whitespace-nowrap rounded-lg text-sm font-medium transition-colors disabled:pointer-events-none disabled:opacity-45 [&_svg]:pointer-events-none [&_svg]:shrink-0",
        VARIANTS[variant],
        SIZES[size],
        className,
      )}
      {...props}
    />
  );
}
