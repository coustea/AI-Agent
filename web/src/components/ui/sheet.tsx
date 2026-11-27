import * as React from "react";
import * as DialogPrimitive from "@radix-ui/react-dialog";

import { cn } from "@/lib/utils";

export const Sheet = DialogPrimitive.Root;
export const SheetTitle = DialogPrimitive.Title;

export function SheetContent({
  side = "right",
  className,
  children,
  ...props
}: React.ComponentProps<typeof DialogPrimitive.Content> & {
  side?: "left" | "right";
}) {
  return (
    <DialogPrimitive.Portal>
      <DialogPrimitive.Overlay className="fixed inset-0 z-50 bg-black/55" />
      <DialogPrimitive.Content
        className={cn(
          "fixed inset-y-0 z-50 flex h-full flex-col bg-sidebar text-foreground shadow-lg",
          side === "left"
            ? "left-0 border-r border-border"
            : "right-0 border-l border-border",
          className,
        )}
        {...props}
      >
        {children}
      </DialogPrimitive.Content>
    </DialogPrimitive.Portal>
  );
}
