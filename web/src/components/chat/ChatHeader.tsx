import {
  Loader2,
  Menu,
  PanelLeftOpen,
  PanelRight,
  SquarePen,
} from "lucide-react";

import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

interface ChatHeaderProps {
  title: string;
  hasMessages: boolean;
  streaming: boolean;
  workspaceCount: number;
  hasNewFiles: boolean;
  sidebarOpen: boolean;
  workspaceOpen: boolean;
  onOpenMobileSidebar: () => void;
  onOpenDesktopSidebar: () => void;
  onCreateConversation: () => void;
  onToggleWorkspace: () => void;
}

export function ChatHeader({
  title,
  hasMessages,
  streaming,
  workspaceCount,
  hasNewFiles,
  sidebarOpen,
  workspaceOpen,
  onOpenMobileSidebar,
  onOpenDesktopSidebar,
  onCreateConversation,
  onToggleWorkspace,
}: ChatHeaderProps) {
  return (
    <header className="flex h-12 shrink-0 items-center justify-between gap-3 border-b border-border/70 bg-background/95 px-3 backdrop-blur-xs sm:px-4">
      <div className="flex min-w-0 items-center gap-1.5">
        <Button
          type="button"
          variant="ghost"
          size="icon"
          aria-label="打开对话列表"
          onClick={onOpenMobileSidebar}
          className="size-8 text-muted-foreground hover:text-foreground lg:hidden"
        >
          <Menu className="size-4" aria-hidden="true" />
        </Button>

        {!sidebarOpen && (
          <div className="hidden items-center gap-1 lg:flex">
            <Button
              type="button"
              variant="ghost"
              size="icon"
              aria-label="展开侧边栏"
              onClick={onOpenDesktopSidebar}
              className="size-8 text-muted-foreground hover:text-foreground"
            >
              <PanelLeftOpen className="size-4" aria-hidden="true" />
            </Button>
            <Button
              type="button"
              variant="ghost"
              size="icon"
              aria-label="新建对话"
              onClick={onCreateConversation}
              className="size-8 text-muted-foreground hover:text-foreground"
            >
              <SquarePen className="size-4" aria-hidden="true" />
            </Button>
          </div>
        )}

        <div className="flex min-w-0 items-center gap-2 pl-1">
          <h1 className="truncate text-[13px] font-medium text-foreground">
            {hasMessages ? title : "新对话"}
          </h1>

          {streaming && (
            <span className="inline-flex shrink-0 items-center gap-1.5 rounded-full border border-border bg-muted/70 px-2 py-0.5 text-[11px] text-muted-foreground">
              <Loader2 className="size-3 animate-spin text-foreground" aria-hidden="true" />
              <span>执行中</span>
            </span>
          )}
        </div>
      </div>

      <Button
        type="button"
        variant={workspaceOpen ? "secondary" : "ghost"}
        size="sm"
        onClick={onToggleWorkspace}
        aria-label={workspaceOpen ? "收起工作区产物面板" : "展开工作区产物面板"}
        className={cn(
          "relative h-8 gap-1.5 rounded-lg px-2.5 text-xs font-medium",
          workspaceOpen
            ? "border border-border bg-muted text-foreground"
            : "text-muted-foreground hover:text-foreground",
        )}
      >
        <PanelRight className="size-3.5" aria-hidden="true" />
        <span className="hidden sm:inline">产物</span>
        {workspaceCount > 0 && (
          <span className="inline-flex h-4 min-w-4 items-center justify-center rounded-md bg-background px-1 font-mono text-[10px] tabular-nums text-foreground ring-1 ring-border">
            {workspaceCount}
          </span>
        )}
        {hasNewFiles && !workspaceOpen && (
          <span
            className="size-1.5 rounded-full bg-foreground"
            aria-label="有新生成的工作区文件"
          />
        )}
      </Button>
    </header>
  );
}
